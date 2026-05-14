import os
import csv
import sys
import math
import numpy as np
import struct
import glob
import pyvista as pv
from pathlib import Path
from scipy.spatial import cKDTree

# Path to the directory containing the .pyd file
pyd_dir_win = os.path.abspath(os.path.join(os.path.dirname(__file__), "py/Release"))
if pyd_dir_win not in sys.path:
  sys.path.append(pyd_dir_win)

if os.name == "nt":
  os.add_dll_directory(pyd_dir_win)

import typedsender  # noqa: E402
import time  # noqa: E402
import sys  # noqa: E402

################################
# Mesh Utils

def read_bin_file(filepath: str, ncol: int = 3) -> np.ndarray:
  with open(filepath, "rb") as file:
    content = file.read()

  if len(content) < 8:
    raise ValueError(f"Invalid bin file '{filepath}': missing size header")

  size = struct.unpack("Q", content[0:8])[0]
  payload = content[8 : (size + 1) * 8]
  data = [d[0] for d in struct.iter_unpack("d", payload)]
  if len(data) != size:
    raise ValueError(
        f"Invalid bin file '{filepath}', expect {size}, found {len(data)}"
    )

  nrow, r = divmod(size, ncol)
  if r != 0:
    raise ValueError(
        f"Invalid column count {ncol}, can not reshape with size {size}"
    )
  return np.reshape(np.array(data, dtype=np.float64), (nrow, ncol))

def nn_index_map(mesh_vertexes: np.ndarray, field_vertexes: np.ndarray) -> np.ndarray:
  mesh_vertexes = np.ascontiguousarray(mesh_vertexes, dtype=np.float64)
  field_vertexes = np.ascontiguousarray(field_vertexes, dtype=np.float64)
  tree = cKDTree(field_vertexes)
  _, idx = tree.query(mesh_vertexes, k=1, workers=-1)
  return np.asarray(idx, dtype=np.int_).reshape(-1, 1)

def load_mesh(mesh_path: str) -> pv.DataSet:
  try:
    obj = pv.read(mesh_path).get_block(0).get_block(0).get_block(0)
  except Exception as exc:
    raise ValueError(f"failed to read mesh from '{mesh_path}'") from exc

  if not isinstance(obj, pv.DataSet):
    raise ValueError(
      "loaded mesh is not pyvista.DataSet, "
      f"actual type: {type(obj).__name__}"
    )
  return obj

# def triangulate_mesh(mesh: pv.DataSet, field_vertexes: np.ndarray | None) -> tuple[TriMesh, np.ndarray]:
#   if not isinstance(mesh, pv.DataSet):
#     raise ValueError("mesh must be pyvista.DataSet")
# 
#   if field_vertexes is None:
#     field_vertexes = np.asarray(mesh.points, dtype=np.float64)
#   else:
#     field_vertexes = np.asarray(field_vertexes, dtype=np.float64)
#     if field_vertexes.ndim != 2 or field_vertexes.shape[1] != 3:
#       raise ValueError("field_vertexes must be shape (m, 3)")
#     if field_vertexes.shape[0] == 0:
#       raise ValueError("field_vertexes must not be empty")
# 
#   surface_mesh = mesh.extract_surface().triangulate()
#   vertexes = np.asarray(surface_mesh.points, dtype=np.float64)
#   triangles = np.asarray(surface_mesh.faces.reshape(-1, 4)[:, 1:], dtype=np.int_)
#   trimesh = TriMesh(vertexes=vertexes, triangles=triangles)
#   sub_indexes = nn_index_map(trimesh.vertexes, field_vertexes)
#   return trimesh, sub_indexes

################################
# Schema Builder

def build_schema():
  generator = typedsender.SchemaGenerator()
  generator.set_schema_info("DemoSchema", "Demo Schema Description", 1, 0, 0)
  generator.add_vector_def(1, "vec_dynamic", "Dynamic length vector", 0, [])
  generator.add_vector_def(2, "vec_1", "Length 1 vector", 1, [0.0])
  generator.add_vector_def(3, "speed_vec", "a vec3 for speed", 3, [0.0, 0.0, 0.0])
  generator.add_trimesh_def(
    4,
    "simple_mesh",
    "A simple triangle mesh",
    [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
    [(0, 1, 2)],
    [("stress", "stress desc"), ("strain", "strain desc")],
    )
  generator.add_namedtuple_def(
    5,
    "point_data",
    "Point data with named fields",
    [("temperature", "temperature desc"), ("pressure", "pressure desc")],
    [20.0, 1.0],
    )
  sig, schema_buffer = generator.build_schema_buffer()
  print("Schema Signature:", sig.hex())

def main():
  print("=== Python Demo Server ===")

  # Load schema_buffer here
  schema_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "robot.scb"))
  with open(schema_path, "rb") as f:
    schema_buffer = f.read()

  manager = typedsender.SenderManager(schema_buffer)
  transport = typedsender.ZMQResTransport("tcp://*:5556")
  transport.set_on_client_connected(lambda: print("Client connected!"))

  manager.set_transport(transport)

  # Load sender
  # FIXME
  # tcp_x_sender = manager.get_namedtuple_sender(55, ["value"])
  # tcp_y_sender = manager.get_namedtuple_sender(56, ["value"])
  # tcp_z_sender = manager.get_namedtuple_sender(57, ["value"])

  trimesh_senders = [
    manager.get_trimesh_sender(60),
    manager.get_trimesh_sender(61),
    manager.get_trimesh_sender(62),
  ]

  # torque_1_x_sender = manager.get_namedtuple_sender(67, ["value"]);
  # torque_1_y_sender = manager.get_namedtuple_sender(68, ["value"]);
  # torque_1_z_sender = manager.get_namedtuple_sender(69, ["value"]);
  # torque_2_x_sender = manager.get_namedtuple_sender(70, ["value"]);
  # torque_2_y_sender = manager.get_namedtuple_sender(71, ["value"]);
  # torque_2_z_sender = manager.get_namedtuple_sender(72, ["value"]);
  # namedtuple_sender = manager.get_namedtuple_sender(0, [])

  transport.session_begin()
  manager.session_initializing(1)

  # tcp_x_sender.send_init({"value": 0})
  # tcp_y_sender.send_init({"value": 0})
  # tcp_z_sender.send_init({"value": 0})

  for trimesh_sender in trimesh_senders:
    trimesh_sender.send_init({"stress_x": []})

  # joint_1_base_fx,
  # joint_1_base_fy,
  # joint_1_base_fz,
  # joint_1_base_tx,
  # joint_1_base_ty,
  # joint_1_base_tz,

  pid_table = [i for i in range(36)]
  ddd_senders = [manager.get_namedtuple_sender(i, ["value"]) for i in pid_table]

  manager.session_initialized()

  ################################
  # Send oxoyoze1e2e3


  ddd = []
  # torque_2_y_sender = ;
  with open("./data/Adams_Results.csv", "r", encoding="utf-8", newline="") as handle:
    reader = csv.DictReader(handle);
    fieldnames = reader.fieldnames

    includes = [i for i in fieldnames if i.endswith("_ox") or i.endswith("_oy") or i.endswith("_oz") or i.endswith("_e1") or i.endswith("_e2") or i.endswith("_e3")]

    print(includes)
    assert len(includes) % 6 == 0
    assert len(pid_table) == len(includes)

    rows = list(reader)
    for idx, field in enumerate(includes):
      dd = []
      for row in rows:
        dd.append(row[field])
      print(len(dd))
      assert len(dd) > 0
      ddd.append(dd)

  for id_idx in range(len(pid_table))[-15:]:
    sender = ddd_senders[id_idx]
    step = 10.0 / len(ddd[id_idx])
    for frame_idx, v in enumerate(ddd[id_idx]):
      t = step * frame_idx;
      err = sender.send_frame(t, {"value": float(v)})
      assert len(err) == 0, err
    time.sleep(0.01)

  time.sleep(10)
  return

  ################################
  # Send TriMesh Frames

  mesh_paths = [
    "./data/Robot/link_2.cgns",
    "./data/Robot/link_3.cgns",
    "./data/Robot/link_4.cgns",
  ]
  bin_dirs = [
    "./data/Robot/link_2_stress",
    "./data/Robot/link_3_stress",
    "./data/Robot/link_4_stress",
  ]
  for i in range(3):
    trimesh_sender = trimesh_senders[i]
    mesh_path = mesh_paths[i]
    bin_dir = bin_dirs[i]
    mesh = pv.read(mesh_path).get_block(0).get_block(0).get_block(0)

    bin_files = sorted(
      Path(bin_dir).glob("snapshot_*.bin"),
      key=lambda p: float(p.stem.split("_", 1)[1]),
    )
    timesteps = [float(p.stem.split("_", 1)[1]) for p in bin_files]

    for idx, t in enumerate(timesteps):
      bin_file = bin_files[idx]
      points = read_bin_file(bin_file, 3)
      point_idx = nn_index_map(mesh.points, points).ravel()
      stress = points[point_idx]
      mesh.point_data["stress"] = stress
      surface_mesh = mesh.extract_surface().triangulate()
      
      stress_x = surface_mesh.point_data["stress"][:,0].astype(float).tolist()
      stress_y = surface_mesh.point_data["stress"][:,1].astype(float).tolist()
      stress_z = surface_mesh.point_data["stress"][:,2].astype(float).tolist()
      ret = trimesh_sender.send_frame(t, {"stress_x": stress_x, "stress_y": stress_y, "stress_z": stress_z, "stress_xy": stress_x, "stress_yz": stress_x, "stress_xz": stress_x})
      print(f"Sending {mesh_path} {bin_file}:{t} -> {ret}")
      time.sleep(0.1)

  # Send Frames 
  # for i in range(300):
  #   t = 0.1*i

  #   tcp_x_sender.send_frame(t, {"value": math.sin(t)*1})
  #   tcp_y_sender.send_frame(t, {"value": math.sin(t)*0.5})
  #   tcp_z_sender.send_frame(t, {"value": math.sin(t)*0.2})

  #   torque_1_x_sender.send_frame(t, {"value": 1.2 * math.sin(t)})
  #   torque_1_y_sender.send_frame(t, {"value": 0.7 * math.sin(1.7 * t + 0.8)})
  #   torque_1_z_sender.send_frame(t, {"value": 0.4 + 0.9 * math.cos(0.6 * t + 1.1)})

  #   torque_2_x_sender.send_frame(t, {"value": 2.0 * math.sin(0.9 * t + 0.3)})
  #   torque_2_y_sender.send_frame(t, {"value": -1.3 + 1.6 * math.cos(1.4 * t)})
  #   torque_2_z_sender.send_frame(t, {"value": 1.1 * math.sin(2.2 * t + 2.0)})

  #   print(f"{i} sent")
  #   time.sleep(1);

  time.sleep(10.0)
  transport.session_end()
  transport.stop()

if __name__ == "__main__":
  main()
