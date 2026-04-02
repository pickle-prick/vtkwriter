import sys
import csv
import time
import json
import asyncio
import glob
import typing as t
import argparse
import pyvista as pv
from pathlib import Path
from functools import partial
from enum import Enum
from websockets import ConnectionClosedOK
from websockets.asyncio.server import serve, ServerConnection 
from dataclasses import dataclass, field, asdict

################################
## Basic types

type Vector3 = tuple[float,float,float]

class DataSourceKind(Enum):
  Invalid = -1
  TriMesh = 0
  NamedArray = 1
  Vector = 2

################################
## Frame

@dataclass
class VectorFrame:
  id: int
  timestep: float
  translate: Vector3
  rotation: Vector3

  def to_str(self) -> str:
    payload = {
      "id": self.id,
      "kind": "Vector",
      "timestep": self.timestep,
      "data": [*self.translate, *self.rotation]
    }
    return json.dumps(payload)

@dataclass
class TriMeshFrame:
  id: int
  timestep: float

  def to_str(self) -> str:
    payload = {
      "id": self.id,
      "kind": "TriMesh",
      "timestep": self.timestep,
      # "data": [*self.translate, *self.rotation]
    }
    return json.dumps(payload)

################################
## DataSource

@dataclass
class DataSource:
  id: int = -1
  kind: DataSourceKind = DataSourceKind.Invalid
  name: str = ""

  def compile(self) -> dict:
    return dict()

  def __aiter__(self) -> t.AsyncIterator[str]:
    raise StopAsyncIteration

  def len(self) -> int:
    return 0

@dataclass
class VectorDataSource(DataSource):
  kind: DataSourceKind = DataSourceKind.Vector
  frames: list[VectorFrame] = field(default_factory=list)

  @classmethod
  def from_csvpath(cls, id:int, csvpath:str) -> t.Self:
    prefix = csvpath.split("\\")[1][:-7]
    name = prefix+"transform"

    frames: list[VectorFrame] = []
    with open(csvpath, "r", encoding="utf-8", newline="") as handle:
      reader = csv.DictReader(handle)
      for row in reader:
        timestep = float(row["TIME"])
        translate = (float(row[f"{prefix}ox"]), float(row[f"{prefix}oy"]), float(row[f"{prefix}oz"]))
        rotation = (float(row[f"{prefix}e1"]), float(row[f"{prefix}e2"]), float(row[f"{prefix}e3"]))
        frames.append(VectorFrame(id, timestep, translate, rotation))
    return cls(id=id, frames=frames, name=name)

  def compile(self) -> dict:
    ret = dict(id=self.id, name=self.name, kind="Vector", length=6)
    return ret

  async def __aiter__(self) -> t.AsyncIterator[str]:
    for frame in self.frames:
      yield frame.to_str()

  def len(self) -> int:
    return len(self.frames)

@dataclass
class TriMeshDataSource(DataSource):
  kind: DataSourceKind = DataSourceKind.TriMesh
  frames: list[TriMeshFrame] = field(default_factory=list)
  cgns_path:Path = Path("")
  mesh:t.Any = None

  @classmethod
  def from_cgnspath(cls, id:int, cgns:str) -> t.Self:
    mesh = pv.read(cgns).get_block(0).get_block(0).get_block(0)
    cgns_path = Path(cgns)
    return cls(id=id, cgns_path=cgns_path, mesh=mesh, name=cgns_path.stem)

  def compile(self) -> dict:
    #error = gen.add_trimesh_def(
    #    schema_id,
    #    port_spec.name,
    #    ty.description,
    #    vertices,
    #    indices,
    #    [(prop.name, prop.description) for prop in ty.properties]
    #)

    ret = dict(id=self.id, name=self.name, kind="TriMesh")
    if self.mesh:
      surface_mesh = self.mesh.extract_surface().triangulate()
      vertices = [tuple(p) for p in surface_mesh.points.tolist()]
      raw_faces = surface_mesh.faces.reshape(-1, 4)[:, 1:]
      faces = [tuple(f) for f in raw_faces.tolist()]
      ret["vertices"] = vertices
      ret["faces"] = faces
    return ret

  async def __aiter__(self) -> t.AsyncIterator[str]:
    for frame in self.frames:
      yield frame.to_str()

  def len(self) -> int:
    return len(self.frames)

type SourceFrame = t.Tuple[int, str]
async def merge_sources(sources: list[DataSource]) -> t.AsyncIterator[SourceFrame]:
  queue:asyncio.Queue[SourceFrame|None] = asyncio.Queue()
  finished_count = 0

  async def producer(source: DataSource):
    nonlocal finished_count
    async for frame in source:
      await queue.put((source.id, frame))
    finished_count += 1
    if finished_count == len(sources):
      await queue.put(None)

  for source in sources:
    asyncio.create_task(producer(source))

  while True:
    frame = await queue.get()
    if frame is None:
      break
    yield frame

################################
## Prob

async def handle_session(websocket: ServerConnection, sources:list[DataSource]):
  print("Connection established")
  pool = merge_sources(sources)
  await asyncio.sleep(3.0)
  try:
    async for frame in pool:
      print("frame sent")
      # await websocket.send(frame[1], text=False)
      await websocket.send(frame[1], text=True)
  except ConnectionClosedOK:
    print("Connection ended")
    return

  # while 1:
  #   try:
  #     data = await websocket.recv(decode=False)
  #   except ConnectionClosedOK:
  #     return

def start_server(host:str, port:int, sources:list[DataSource]):
  async def start():
    async with serve(partial(handle_session, sources=sources), host, port, max_size=None) as server:
      print(f"Listening on {host}:{port}")
      await server.serve_forever()
  asyncio.run(start())

def main() -> int:
  parser = argparse.ArgumentParser(description="SimpleDataSource")
  parser.add_argument("cmd", type=str)
  args = parser.parse_args()

  ################################
  # Create some sources

  sources:list[DataSource] = []
  id:int = 0

  CSV_PATH = "./data/Robot"
  CSV_PATHS = glob.glob(f"{CSV_PATH}/*.csv")
  print(CSV_PATHS)
  for idx, p in enumerate(CSV_PATHS):
    sources.append(VectorDataSource.from_csvpath(idx+id, p))
  id += (idx+1)

  CGNS_PATHS = glob.glob("./data/robot-fem-mesh/*.cgns")
  print(CGNS_PATHS)
  for idx, p in enumerate(CGNS_PATHS):
    source = TriMeshDataSource.from_cgnspath(idx+id, p)
    # source.mesh.plot()
    sources.append(source)
  id += (idx+1)

  if args.cmd == "compile":
    ret = [source.compile() for source in sources]
    with open("./data/t.json", "w", encoding="utf8") as f:
      json.dump(ret, f, indent=2)
  elif args.cmd == "serve":
    start_server("127.0.0.1", 5554, sources)

  return 0

if __name__ == "__main__":
  sys.exit(main())
