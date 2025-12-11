import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import typing as t
import asyncio
from dataclasses import dataclass
from core import Reader, Frame, PipelineInformation
import vtk

# STEP_DURATION = 0.02
STEP_DURATION = 0.05

class VtkFrameReader(Reader):
  def __init__(self):
    self.frame_index:int = 0
    self.is_dirty = False
    self.files:t.List[str] = []
    # self.reader = vtk.PolyDataReader()
    self.reader = vtk.vtkXMLPolyDataReader()
    # self.reader = vtk.vtkXMLUnstructuredGridReader()
    self.cached:t.List[vtk.DataSet] = []

  def load_files(self, files:t.List[str]) -> None:
    self.files = files
    self.cached = []
    for f in files:
      self.reader.SetFileName(f)
      self.reader.Modified()
      self.reader.Update()

      ret = self.reader.GetOutput(0)

      # clean = vtk.vtkCleanUnstructuredGrid()
      # clean.SetInputData(ret)
      # clean.Update()
      # ret = clean.GetOutput()

      # geom = vtk.vtkGeometryFilter()
      # geom.SetInputData(self.reader.GetOutput())
      # geom.Update()
      # polydata = geom.GetOutput(0)

      dataset = vtk.vtkPolyData()
      dataset.DeepCopy(ret) # NOTE: we need to deep copy to make cache work
      self.cached.append(dataset)

  def __aiter__(self):
    self.frame_index = 0
    return self

  async def __anext__(self) -> Frame:
    if self.frame_index >= len(self):
      raise StopAsyncIteration

    i = self.frame_index
    frame = Frame(PipelineInformation(len(self), 1.0), i, STEP_DURATION*i, self.cached[i])
    self.frame_index += 1
    return frame

  def __len__(self) -> int:
    return len(self.files)

async def test():
  files = [f"./data/GearNew/GEAR1_{i}.vtp" for i in range(5)]
  # files = [f"./data/Gear/test_{i}.vtu" for i in range(2)]
  reader = VtkFrameReader() 
  reader.load_files(files)
  print(len(reader))
  async for frame in reader:
    print(frame.frame_index, frame.frame_time)

  import pyvista as pv

  pl = pv.Plotter()
  async for frame in reader:
    grid = frame.dataset
    pl.add_mesh(grid, scalars="pstress", rng=[0,300], cmap="jet")
    break
  pl.show()

  # mesh = grid.extract_surface()
  # mesh.plot(scalars="pstress", rng=[0,300], cmap="jet", interpolate_before_map=True, color="w")

if __name__ == "__main__":
  asyncio.run(test())
