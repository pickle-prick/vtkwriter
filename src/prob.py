import vtk
import asyncio
import argparse
import websockets
from dataclasses import dataclass
import typing as t

FORMAT_VERSION = "0.0.1"

################################
## Message

@dataclass
class DataObject:
  type_name:str
  xml:str

  @classmethod
  def zero(cls):
    return cls("","")

@dataclass
class Information:
  name:str
  total_frame_count:int
  frame_index:int
  frame_timestamp:float

  @classmethod
  def zero(cls):
    return cls("", 0,0,0)

@dataclass
class Message:
  key:int
  information: Information
  data_objects: t.List[DataObject]

  @classmethod
  def zero(cls):
    ret = cls(key=0, information=Information.zero(), data_objects=[])
    return ret

def bytes_from_message(msg:Message):
  # ret = "0\n"
  # ret += f"format_version: str = \"{FORMAT_VERSION}\"\n"
  # ret += f"key: s32 = {msg.key}\n"

  # # Information
  # ret += "[Information]\n"
  # ret += f"name: str = \"{msg.information.name}\"\n"
  # ret += f"total_frame_count: s32 = {msg.information.total_frame_count}\n"
  # ret += f"frame_index: u32 = {msg.information.frame_index}\n"
  # ret += f"frame_timestamp: f32 = {msg.information.frame_timestamp}\n"

  # Testing
  ret = str(msg.key)+"\n"
  print(f"{msg.key}, {ret}")
  ret += msg.data_objects[0].xml
  # print(f"xml size: {len(msg.data_objects[0].xml)}")
  return ret

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
## Mesh

def mesh_from_vtk_legacy(path:str):
  reader = vtk.vtkPolyDataReader()
  reader.SetFileName(path)
  decimate = vtk.vtkDecimatePro()
  decimate.SetInputConnection(reader.GetOutputPort(0))
  decimate.SetTargetReduction(0.99)
  decimate.PreserveTopologyOn()
  return decimate

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

  ret = writer.GetOutputString()   # VTK returns bytes or str depending on version
  # ret = ret.encode("utf8")
  return ret

def stub_message(mesh_id:int, msg_id:int) -> Message:
  msg = Message.zero() 
  msg.key = msg_id
  msg.information.name = "Cylinder"

  src = mesh_cylinder()
  if mesh_id == 0: src = mesh_from_vtk_legacy("./data/pressure_field_mesh.vtk")
  if mesh_id == 1: src = mesh_compund()
  if mesh_id == 2: pass
  src.Update()

  mesh = src.GetOutput()
  xml = xml_from_vtk_mesh(mesh)
  msg.data_objects.append(DataObject("PolyData", xml))
  return msg

def test():
  msg = stub_message()

  bs = bytes_from_message(msg) 
  print(bs)
  print()
  print(bs.decode("utf8"))

async def mock(mesh_id:int, msg_id:int):
  uri = "ws://localhost:8080"
  mesh = mesh_cylinder()
  if mesh_id == 0: mesh = mesh_from_vtk_legacy("./data/pressure_field_mesh.vtk")
  if mesh_id == 1: mesh = mesh_compund()
  if mesh_id == 2: pass

  # pipeline
  tail = mesh
  if mesh_id == 0:
    tail = vtk.vtkReverseSense()
    tail.SetInputConnection(mesh.GetOutputPort())
    # tail.ReverseNormalsOn()

  transform = vtk.vtkTransform()
  transform_filter = vtk.vtkTransformPolyDataFilter()
  transform_filter.SetTransform(transform)
  transform_filter.SetInputConnection(tail.GetOutputPort())
  sink = transform_filter

  # lut
  rng = (-2321.6083984375, 1010.710693359375)
  lut = default_lut(rng, 256*4)

  while 1:
    try:
      async with websockets.connect(uri, max_size=None) as ws:
        while 1:
          frame_begin_ms = asyncio.get_event_loop().time() * 1000

          msg = Message.zero() 
          msg.key = msg_id
          msg.information.name = "Cylinder"

          # update mesh
          transform.RotateX(4.5)
          sink.Update()
          polydata = transform_filter.GetOutput()
          lut_applied = apply_lut(polydata, lut, "p")

          # add per-vertex colors
          # if lut_applied == 0:
          #   colors = vtk.vtkUnsignedCharArray()
          #   colors.SetNumberOfComponents(3) # RGB
          #   colors.SetName("Colors")

          #   # generate a random color
          #   r = random.randint(0,255)
          #   g = random.randint(0,255)
          #   b = random.randint(0,255)

          #   for _ in range(polydata.GetNumberOfPoints()):
          #     colors.InsertNextTuple3(r,g,b)

          #   polydata.GetPointData().SetScalars(colors)

          xml = xml_from_vtk_mesh(polydata)
          msg.data_objects.append(DataObject("PolyData", xml))
          bs:bytes = bytes_from_message(msg).encode("utf8")

          # await ws.send(bs)
          await ws.send(bs, text=True)
          # await ws.send("123")
          print(f"{frame_begin_ms}, {msg.key} {mesh_id}")
          await asyncio.sleep(0.0)
    except:
      await asyncio.sleep(3)

async def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("msg_id", type=int, default=0, help="msg_id")
  parser.add_argument("mesh_id", type=int, default=0, help="mesh_id")
  args = parser.parse_args()
  print(args.mesh_id, args.msg_id)
  await mock(args.mesh_id, args.msg_id)

if __name__ == "__main__":
  asyncio.run(main())
