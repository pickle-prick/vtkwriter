import vtk
import asyncio
import websockets
from dataclasses import dataclass
import typing as t
import random
import matplotlib.pyplot as plt

################################
## Mesh

def mesh_from_vtk_legacy(path:str):
  reader = vtk.vtkPolyDataReader()
  reader.SetFileName(path)
  return reader

def mesh_cylinder():
  cylinder = vtk.vtkCylinderSource()
  cylinder.SetResolution(8)
  return cylinder

def mesh_compund():
  # Cylinder
  cylinder = vtk.vtkCylinderSource()
  cylinder.SetResolution(16)
  cylinder.SetHeight(2.0)
  cylinder.SetRadius(0.5)
  cylinder.Update()

  # Sphere
  sphere = vtk.vtkSphereSource()
  sphere.SetRadius(0.6)
  sphere.SetThetaResolution(16)
  sphere.SetPhiResolution(16)
  sphere.SetCenter(0, 0, 1.0)
  sphere.Update()

  # Cone
  cone = vtk.vtkConeSource()
  cone.SetHeight(1.0)
  cone.SetRadius(0.3)
  cone.SetResolution(16)
  cone.SetCenter(0, 0, -1.0)
  cone.Update()

  # -------------------------
  # 2. Transform each primitive
  # -------------------------
  transform = vtk.vtkTransform()
  transform.RotateX(30)
  transform_filter = vtk.vtkTransformPolyDataFilter()
  transform_filter.SetTransform(transform)
  transform_filter.SetInputConnection(sphere.GetOutputPort())
  transform_filter.Update()

  # -------------------------
  # 3. Combine meshes
  # -------------------------
  append_filter = vtk.vtkAppendPolyData()
  append_filter.AddInputData(cylinder.GetOutput())
  append_filter.AddInputData(transform_filter.GetOutput())
  append_filter.AddInputData(cone.GetOutput())
  append_filter.Update()

  # -------------------------
  # 4. Clean & triangulate
  # -------------------------
  clean_filter = vtk.vtkCleanPolyData()
  clean_filter.SetInputConnection(append_filter.GetOutputPort())
  clean_filter.Update()

  triangulate = vtk.vtkTriangleFilter()
  triangulate.SetInputConnection(clean_filter.GetOutputPort())
  triangulate.Update()

  # -------------------------
  # 5. Compute normals
  # -------------------------
  normals = vtk.vtkPolyDataNormals()
  normals.SetInputConnection(triangulate.GetOutputPort())
  normals.ComputePointNormalsOn()
  normals.Update()

  return normals

mesh_1 = mesh_from_vtk_legacy("./data/pressure_field_mesh.vtk")
mesh_2 = mesh_cylinder()
mesh_3 = mesh_compund()

################################
## Lut

@dataclass
class Lut:
  lut:vtk.vtkLookupTable
  table_size:int
  rng:tuple[int,int]

def default_lut(rng:tuple[int,int], table_size=256) -> Lut:
  lut = vtk.vtkLookupTable()
  lut.SetNumberOfTableValues(table_size)
  lut.SetRange(rng[0], rng[1])
  lut.Build()
  for i in range(table_size):
    t = i / (table_size - 1)
    r = 1.0
    g = 1.0 - t
    b = 1.0 - t
    lut.SetTableValue(i, r, g, b, 1.0)
  return Lut(lut, table_size, rng)

def get_vtk_lut_from_matplotlib(map_name: str, rng:tuple[int,int], num_colors: int = 256) -> vtk.vtkLookupTable:
  cmap = plt.get_cmap(map_name)
  
  lut = vtk.vtkLookupTable()
  lut.SetNumberOfTableValues(num_colors)
  lut.Build()
  lut.SetRange(rng[0], rng[1])
  
  for i in range(num_colors):
    t = i / (num_colors - 1)
    r, g, b, a = cmap(t)  # returns floats in 0..1
    lut.SetTableValue(i, r, g, b, a)
  
  ret = Lut(lut, num_colors, rng)
  return ret

def apply_lut(mesh:vtk.vtkPolyData, lut:Lut, scalar:str) -> int:
  ret = 0
  point_data = mesh.GetPointData()
  pressure_array = point_data.GetScalars(scalar)

  if pressure_array:
    ret = 1
    color_array = vtk.vtkUnsignedCharArray()
    color_array.SetNumberOfComponents(3)
    color_array.SetName("Colors")

    for i in range(pressure_array.GetNumberOfTuples()):
      pressure_value = pressure_array.GetValue(i)
      normalized_value = (pressure_value-lut.rng[0]/(lut.rng[1]-lut.rng[0]))
      # color_index = int(lut.lut.GetHexValue(pressure_value))
      color_index = int(normalized_value*(lut.table_size-1))
      color = lut.lut.GetTableValue(color_index)
      color_array.InsertNextTuple3(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
    point_data.AddArray(color_array)
    point_data.SetScalars(color_array)
  return ret

def get_color_map_lut(map_name: str) -> vtk.vtkLookupTable:
  color_map = vtk.vtkColorMaps.GetColorMap(map_name)
  vtk_color_table = vtk.vtkLookupTable()
  
  # Configure LUT as per the selected color map
  color_map.ApplyTo(vtk_color_table)
  
  return vtk_color_table

################################
## Serialization

def legacy_from_vtk_mesh(mesh:vtk.vtkPolyData):
  writer = vtk.vtkPolyDataWriter()
  # writer.SetFileTypeToBinary()
  writer.SetFileTypeToASCII()
  writer.SetInputData(mesh)
  writer.SetWriteToOutputString(True)
  writer.Write()
  data = writer.GetOutputString()
  return data

def xml_from_vtk_mesh(mesh):
  """
  Serialize a vtkPolyData mesh to bytes using modern XML VTK format (.vtp).
  Returns raw bytes suitable for sending over network.
  """
  writer = vtk.vtkXMLPolyDataWriter()
  writer.SetInputData(mesh)
  writer.SetDataModeToBinary()      # Binary XML format
  writer.WriteToOutputStringOn()    # Write to memory buffer
  writer.SetCompressorTypeToLZ4()
  writer.Write()

  data = writer.GetOutputString()   # VTK returns bytes or str depending on version
  # if isinstance(data, str):
  #   data = data.encode('latin1')  # ensure raw bytes
  return data

################################
## Entry

async def mesh_handler(websocket:websockets.ServerConnection):
  print(f"[{websocket.remote_address}] connected")
  transform = vtk.vtkTransform()
  rng = (-2321.6083984375, 1010.710693359375)
  lut = default_lut(rng, 256*4)
  # "viridis", "plasma", "cividis"
  # lut = get_vtk_lut_from_matplotlib("cividis", rng)
  # mesh = random.choice([mesh_1, mesh_2, mesh_3])
  # mesh = random.choice([mesh_1, mesh_2, mesh_3])
  mesh = mesh_1
  while True:
    frame_begin_ms = asyncio.get_event_loop().time() * 1000

    transform.RotateX(0.5)
    transform_filter = vtk.vtkTransformPolyDataFilter()
    transform_filter.SetTransform(transform)
    transform_filter.SetInputConnection(mesh.GetOutputPort())
    transform_filter.Update()
    polydata = transform_filter.GetOutput()
    lut_applied = apply_lut(polydata, lut, "p")

    # add per-vertex colors
    if lut_applied == 0:
      colors = vtk.vtkUnsignedCharArray()
      colors.SetNumberOfComponents(3) # RGB
      colors.SetName("Colors")

      # generate a random color
      r = random.randint(0,255)
      g = random.randint(0,255)
      b = random.randint(0,255)

      for _ in range(polydata.GetNumberOfPoints()):
        colors.InsertNextTuple3(r,g,b)

      polydata.GetPointData().SetScalars(colors)

    mesh_bytes = xml_from_vtk_mesh(polydata)
    print(f"size of mb: {len(mesh_bytes) / 1024 / 1024:.2f}, {type(mesh_bytes)}")
    send_begin = asyncio.get_event_loop().time()
    # NOTE: this is limited by the reader side recv handling speed, ue default websocket callback interval is low I assume
    await websocket.send(mesh_bytes)
    print(f"Frame sent took: {(asyncio.get_event_loop().time() - send_begin)*1000:.2f} ms")
    print("----")

    frame_end_ms = asyncio.get_event_loop().time() * 1000
    dt = (frame_end_ms - frame_begin_ms) / 1000.0
    print(f"Total frame time: {dt*1000:.2f} ms")
    print(f"FPS: {1.0/dt:.2f}")

    # await asyncio.sleep(0)
    await asyncio.sleep(3.00)

async def main():
  async with websockets.serve(mesh_handler, "127.0.0.1", 1080, max_size=None):
    print("websocket server running at ws://localhost:1080")
    await asyncio.Future()

if __name__ == "__main__":
  asyncio.run(main())
