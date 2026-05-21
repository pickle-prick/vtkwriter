import numpy as np
import pyvista as pv

def triangle_only(poly: pv.PolyData) -> pv.PolyData:
  # Ensure polygon faces are triangles first.
  poly = poly.triangulate(pass_verts=False, pass_lines=False)

  faces = poly.faces.reshape((-1, 4))

  # Keep only rows like [3, a, b, c].
  faces = faces[faces[:, 0] == 3]

  return pv.PolyData(poly.points, faces)

def main():
  path = "./clean.obj"
  mesh = pv.read(path)
  print("points:", mesh.n_points)
  print("faces:", mesh.n_faces_strict)
  mesh.plot()
  return

  path = "./data/1.obj"
  mesh = pv.read(path)

  print(type(mesh))
  if not isinstance(mesh, pv.PolyData):
    mesh = mesh.extract_surface()
  print("all triangles:", mesh.is_all_triangles)
  if not mesh.is_all_triangles:
    mesh = mesh.triangulate()
  # points: 84663219
  # faces: 28221073
  print("before clean points:", mesh.n_points)
  print("before clean faces:", mesh.n_faces_strict)

  mesh = mesh.clean(tolerance=0.0)
  # Clean can change cell layout, so triangulate again and drop verts/lines again.
  mesh = triangle_only(mesh)
  # mesh = mesh.triangulate(pass_verts=False, pass_lines=False)
  mesh.save("clean.obj")

  print("after clean points:", mesh.n_points)
  print("after clean faces:", mesh.n_faces_strict)

  # surface = mesh.extract_surface()
  # print(type(surface))
  # print("points:", surface.n_points)
  # print("faces:", surface.n_faces_strict)
  # surface.save("output.obj")

  # reduced = mesh.decimate_pro(
  #   reduction=0.85,
  #   preserve_topology=True,
  # )
  # reduced = mesh.decimate(0.85)
  reduced = mesh.decimate(
    target_reduction=0.85,
    volume_preservation=False,
    attribute_error=False,
  )
  print("reduced points:", reduced.n_points)
  print("reduced faces:", reduced.n_faces_strict)
  reduced.save("reduced.obj")

  # mesh.plot()

if __name__ == "__main__":
  main()
