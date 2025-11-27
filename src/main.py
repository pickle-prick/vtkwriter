import vtk
import struct
import asyncio
import time
import argparse
import websockets
from dataclasses import dataclass
from core import Reader
import typing as t
from reader.fluent_cff import FluentCFFReader
from Envelope import ForwardMessage, DataObject, Information, PipelineInformation
from lut import lut_from_name, apply_lut, default_lut
import flatbuffers

FORMAT_VERSION = "0.0.1"
HOST = "10.0.0.243"
# HOST = "127.0.0.1"
PORT = 8080

################################
## Message

@dataclass
class FrameInfo:
  index:int
  timestep:float
  xml:str

@dataclass
class MessageRecipe:
  total_frame_count:int
  frames:t.List[FrameInfo]

def cooke_message(msg_id:int, recipe:MessageRecipe) -> bytes:
  builder = flatbuffers.Builder(1024)

  # build pipeline information
  PipelineInformation.Start(builder)
  PipelineInformation.AddFrameCount(builder, recipe.total_frame_count)
  pipeline_info = PipelineInformation.End(builder)

  frame_infos = []
  for frame in recipe.frames:
    type_str = builder.CreateString("PolyData") # TODO: support other types, do we really need this?
    xml_str = builder.CreateString(frame.xml)
    DataObject.Start(builder)
    DataObject.AddType(builder, type_str)
    DataObject.AddXml(builder, xml_str)
    data_object = DataObject.End(builder)
    
    Information.Start(builder)
    Information.AddFrameIndex(builder, frame.index)
    Information.AddFrameTimestep(builder, frame.timestep)
    Information.AddDataObject(builder, data_object)
    frame_info = Information.End(builder)
    frame_infos.append(frame_info)

  ForwardMessage.StartInformationsVector(builder, len(frame_infos))
  for frame_info in frame_infos:
    builder.PrependUOffsetTRelative(frame_info)
  informations = builder.EndVector()

  # build message
  ForwardMessage.Start(builder)
  ForwardMessage.AddKey(builder, msg_id)
  ForwardMessage.AddTimestamp(builder, int(time.time())) # TODO: check it later, should we use unix timestamp?
  ForwardMessage.AddPipelineInfo(builder, pipeline_info)
  ForwardMessage.AddInformations(builder, informations)
  msg = ForwardMessage.End(builder)

  builder.Finish(msg)
  ret = builder.Output()
  return bytes(ret)

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

# def stub_message(mesh_id:int, msg_id:int) -> Message:
#   msg = Message.zero() 
#   msg.key = msg_id
#   msg.information.name = "Cylinder"
# 
#   src = mesh_cylinder()
#   if mesh_id == 0: src = mesh_from_vtk_legacy("./data/pressure_field_mesh.vtk")
#   if mesh_id == 1: src = mesh_compund()
#   if mesh_id == 2: pass
#   src.Update()
# 
#   mesh = src.GetOutput()
#   xml = xml_from_vtk_mesh(mesh)
#   msg.data_objects.append(DataObject("PolyData", xml))
#   return msg

# def test():
#   msg = stub_message()
# 
#   bs = bytes_from_message(msg) 
#   print(bs)
#   print()
#   print(bs.decode("utf8"))

async def mock_ws(mesh_id:int, msg_id:int):
  r = FluentCFFReader()
  r.read_project("./data/Fluent-result")
  # r.read_project("./data/3D-Pipe")

  # mesh = mesh_cylinder()
  # if mesh_id == 0: mesh = mesh_from_vtk_legacy("./data/pressure_field_mesh.vtk")
  # if mesh_id == 1: mesh = mesh_compund()
  # if mesh_id == 2: pass

  # # pipeline
  # tail = mesh
  # if mesh_id == 0:
  #   tail = vtk.vtkReverseSense()
  #   tail.SetInputConnection(mesh.GetOutputPort())
  #   # tail.ReverseNormalsOn()

  transform = vtk.vtkTransform()
  transform_filter = vtk.vtkTransformPolyDataFilter()
  transform_filter.SetTransform(transform)
  # transform_filter.SetInputConnection(tail.GetOutputPort())
  # sink = transform_filter

  # # lut
  # rng = (-2321.6083984375, 1010.710693359375)

  lut = lut_from_name("inferno")
  lut.SetValueRange((0,1))
  # lut = default_lut(rng, 256*4)

  writer = None
  uri = f"ws://{HOST}:{PORT}"
  async with websockets.connect(uri, max_size=None) as ws:
    async for frame in r:
      begin_sec = time.perf_counter()
      geom = vtk.vtkGeometryFilter()
      geom.SetInputData(frame.dataset)
      geom.Update()
      polydata = geom.GetOutput(0)

      transform.RotateX(0.15)
      transform_filter.SetInputData(polydata)
      transform_filter.Update()
      polydata = transform_filter.GetOutput(0)

      cell_to_point = vtk.vtkCellDataToPointData()
      cell_to_point.SetInputData(polydata)
      cell_to_point.Update()
      polydata = cell_to_point.GetOutput()
      apply_lut(polydata, lut, "VelocityMag")

      xml = xml_from_vtk_mesh(polydata)
      bs = stub_message(xml, msg_id, frame.frame_index*0.02*1000)
      print(f"processed {(time.perf_counter()-begin_sec)*1000:.4}ms")
      begin_sec = time.perf_counter()
      await ws.send(bs, text=True)
      now = time.perf_counter()
      print(f"sending took {(now-begin_sec)*1000:.4}ms, {len(bs)/(1024*1024):.2}mb, {len(bs)}bytes")
      await asyncio.sleep(0.0)
      # print(f"sent: {i}")

      # update mesh
      # transform.RotateX(4.5)
      # sink.Update()
      # polydata = transform_filter.GetOutput()
      # lut_applied = apply_lut(polydata, lut, "p")
      # xml = xml_from_vtk_mesh(polydata)
      # bs = stub_message(xml, msg_id)

      # await ws.send(bs)
      # await ws.send(bs, text=True)
      # await ws.send("123")
      # print(f"{frame_begin_ms}, {msg.key} {mesh_id}")
  
async def mock_tcp(mesh_id:int, msg_id:int):
  r = FluentCFFReader()
  r.read_project("./data/Fluent-result")
  # r.read_project("./data/3D-Pipe")

  # mesh = mesh_cylinder()
  # if mesh_id == 0: mesh = mesh_from_vtk_legacy("./data/pressure_field_mesh.vtk")
  # if mesh_id == 1: mesh = mesh_compund()
  # if mesh_id == 2: pass

  # # pipeline
  # tail = mesh
  # if mesh_id == 0:
  #   tail = vtk.vtkReverseSense()
  #   tail.SetInputConnection(mesh.GetOutputPort())
  #   # tail.ReverseNormalsOn()

  transform = vtk.vtkTransform()
  transform_filter = vtk.vtkTransformPolyDataFilter()
  transform_filter.SetTransform(transform)
  # transform_filter.SetInputConnection(tail.GetOutputPort())
  # sink = transform_filter

  # # lut
  # rng = (-2321.6083984375, 1010.710693359375)

  lut = lut_from_name("inferno")
  lut.SetValueRange((0,1))
  # lut = default_lut(rng, 256*4)

  writer = None
  try:
    reader, writer = await asyncio.open_connection(HOST, PORT)
    total_frame_count = len(r)
    async for frame in r:
      begin_sec = time.perf_counter()
      geom = vtk.vtkGeometryFilter()
      geom.SetInputData(frame.dataset)
      geom.Update()
      polydata = geom.GetOutput(0)

      transform.RotateX(0.15)
      transform_filter.SetInputData(polydata)
      transform_filter.Update()
      polydata = transform_filter.GetOutput(0)

      cell_to_point = vtk.vtkCellDataToPointData()
      cell_to_point.SetInputData(polydata)
      cell_to_point.Update()
      polydata = cell_to_point.GetOutput()
      apply_lut(polydata, lut, "VelocityMag")

      xml = xml_from_vtk_mesh(polydata)

      # cook message
      recipe = MessageRecipe(total_frame_count, [FrameInfo(frame.frame_index, frame.frame_time, xml)])
      bs = cooke_message(msg_id, recipe)
      print(f"processed {(time.perf_counter()-begin_sec)*1000:.4}ms")

      begin_sec = time.perf_counter()
      header = len(bs)
      header_bytes = struct.pack("=Q", header)
      writer.write(header_bytes+bs)
      await writer.drain()
      now = time.perf_counter()
      print(f"sending took {(now-begin_sec)*1000:.4}ms, {len(bs)/(1024*1024):.2}mb, {len(bs)}bytes")
      await asyncio.sleep(0.0)
      # print(f"sent: {i}")

      # update mesh
      # transform.RotateX(4.5)
      # sink.Update()
      # polydata = transform_filter.GetOutput()
      # lut_applied = apply_lut(polydata, lut, "p")
      # xml = xml_from_vtk_mesh(polydata)
      # bs = stub_message(xml, msg_id)

      # await ws.send(bs)
      # await ws.send(bs, text=True)
      # await ws.send("123")
      # print(f"{frame_begin_ms}, {msg.key} {mesh_id}")
  finally:
    if writer:
      writer.close()
      await writer.wait_closed()

async def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--msg_id", type=int, default=0, help="msg_id")
  parser.add_argument("--mesh_id", type=int, default=0, help="mesh_id")
  args = parser.parse_args()
  print(args.mesh_id, args.msg_id)

  while 1:
    try:
      # await mock_ws(args.mesh_id, args.msg_id)
      await mock_tcp(args.mesh_id, args.msg_id)
      print("OK")
      break
    except Exception as e:
      print(e)
      print("failed, try again in 3 seconds")
      await asyncio.sleep(3.0)

if __name__ == "__main__":
  asyncio.run(main())