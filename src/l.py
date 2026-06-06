import numpy as np
import struct
import pyvista as pv
from pathlib import Path
from scipy.spatial import cKDTree

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

def compute_principal_stress(stress: np.ndarray):
  # slow import
  from ansys.mapdl.reader import _binary_reader

  pstress, isnan = _binary_reader.compute_principal_stress(stress)
  pstress[isnan] = np.nan
  np.nan_to_num(pstress, copy=False)

  return pstress[:, 4]

def nn_index_map(mesh_vertexes: np.ndarray, field_vertexes: np.ndarray) -> np.ndarray:
  mesh_vertexes = np.ascontiguousarray(mesh_vertexes, dtype=np.float64)
  field_vertexes = np.ascontiguousarray(field_vertexes, dtype=np.float64)
  tree = cKDTree(field_vertexes)
  eps, idx = tree.query(mesh_vertexes, k=1, workers=-1)
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

def export_custom_mesh_binary(mesh: pv.PolyData, outpath: str):
  vertices = mesh.points.astype(np.float64)
  vertex_count = len(vertices)

  # Extract the indices, since it is triangulated, each face has 3 indices
  # We flatten the array to get a continuous list of indices
  raw_faces = mesh.faces.reshape(-1, 4)[:, 1:]
  indices = raw_faces.astype(np.uint32) # 32-bit unsigned integers
  index_count = indices.size

  with open(outpath, "wb") as f:
    # Header
    # 'I' represents a 4-byte C unsigned int (uint32)
    f.write(struct.pack("I", vertex_count))
    f.write(struct.pack("I", index_count))

    # Write Vertex Data (vec3f64)
    vertices.tofile(f)
    # Write Index Data (uint32)
    indices.tofile(f)

def load_custom_mesh_binary(filepath: str) -> pv.PolyData:
  with open(filepath, "rb") as f:
    header_bytes = f.read(8)
    assert len(header_bytes) == 8
    vertex_count, index_count = struct.unpack("II", header_bytes)

    vertices_flat = np.fromfile(f, dtype=np.float64, count=vertex_count*3)
    assert len(vertices_flat) == vertex_count*3
    vertices = vertices_flat.reshape(-1, 3)

    indices = np.fromfile(f, dtype=np.uint32, count=index_count)
    assert len(indices) == index_count

  num_faces = index_count//3
  triangles = indices.reshape(num_faces, 3)

  # Prepend a column of 3s to represent the vertex count for each triangle
  padding = np.full((num_faces, 1), 3, dtype=np.uint32)
  faces = np.hstack((padding, triangles)).ravel()

  mesh = pv.PolyData(vertices, faces)
  return mesh

def export_custom_scalars_binary(scalars:np.ndarray, outpath:str):
  with open(outpath, "wb") as f:
    scalars = scalars.astype(np.float32)

    # Header
    f.write(struct.pack("I", len(scalars)))

    # Values
    scalars.tofile(f)

def export(cgns_path:str, points_bin_path:str, bin_search_path:str, outdir: str):
  ################################
  # Read Mesh

  mesh = pv.read(cgns_path).get_block(0).get_block(0).get_block(0)
  mesh = mesh.extract_surface().triangulate()

  # Merge duplicate point
  # cleaned_mesh = mesh.clean(point_merging=True, tolerance=1e-4, absolute=False)
  # n_total = mesh.n_points
  # n_unique = len(np.unique(mesh.points, axis=0))

  ################################
  # Read Points

  points = read_bin_file(points_bin_path, 3)
  # point_idx = nn_index_map(points, mesh.points).ravel()
  point_idx = nn_index_map(mesh.points, points).ravel()
  assert len(np.unique(point_idx)) == len(point_idx), ( "Point index unique check failure")

  ################################
  # Read Bins

  def load_bin(bin_path:str, point_idx:np.ndarray, point_count:int) -> np.ndarray:
    # raw_data = read_bin_file("./data/grinding/Snapshots/snapshot_6.bin", 1)
    # column_count = 6
    # point_data = np.reshape(raw_data, (len(raw_data) // column_count, column_count))
    raw_data = read_bin_file(bin_path, 6)
    assert(len(raw_data) == point_count)
    ret = raw_data[point_idx]
    ret = compute_principal_stress(ret)
    return ret

  scalars_arr = [load_bin(i, point_idx, len(mesh.points)) for i in Path(bin_search_path).glob("*.bin")]

  # Export
  outdir = Path(outdir)
  outdir.mkdir(parents=True, exist_ok=True)
  export_custom_mesh_binary(mesh, outdir.joinpath("mesh.bin"))
  outbindir = outdir.joinpath("bin/")
  outbindir.mkdir(parents=False, exist_ok=True)
  for idx, scalars in enumerate(scalars_arr):
    export_custom_scalars_binary(scalars, str(outbindir.joinpath(f"{idx}.bin")))

  # mesh.point_data["pstress"] = pstress
  # mesh.set_active_scalars("pstress")
  # mesh.plot(show_edges=False)

def main():
  # export("./data/grinding/grinding.cgns", "./data/grinding/points.bin", "./data/grinding/Snapshots/", "./data/grinding/griding_out/")
  export("./data/grinding_simplified/grindingmesh.cgns", "./data/grinding_simplified/points.bin", "./data/grinding_simplified/Snapshots/", "./data/grinding_simplified/griding_out/")

if __name__ == "__main__":
  main()
