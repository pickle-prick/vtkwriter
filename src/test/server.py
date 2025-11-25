import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import asyncio
import vtk
import time
from websockets.asyncio.server import serve, ServerConnection 
from websockets.asyncio.connection import ConnectionClosedOK
from Envelope.ForwardMessage import ForwardMessage
from Envelope.DataObject import DataObject
from Envelope.Information import Information
from threading import Thread, Event, Lock

stop_evt = Event()
lck = Lock()
mapper = vtk.vtkPolyDataMapper()
# mapper.SetArrayName("Colors")
# mapper.SetScalarModeToUsePointData()
mapper.SetScalarVisibility(1)
mapper.SelectColorArray("Colors")
mapper.SetScalarMode(vtk.VTK_SCALAR_MODE_USE_POINT_FIELD_DATA)
# mapper.SetScalarMode(vtk.VTK_SCALAR_MODE_USE_POINT_DATA) # only active scalar
mapper.SetColorModeToDirectScalars()

def render_worker():
  c = vtk.vtkCylinderSource()
  c.SetResolution(8)
  c.Update()

  # mapper.SetInputConnection(c.GetOutputPort())
  global mapper
  mapper.SetInputData(c.GetOutput(0))
  actor = vtk.vtkActor()
  actor.SetMapper(mapper)

  # render
  ren = vtk.vtkRenderer()
  ren.SetBackground(0.9, 0.9, 0.9)
  win = vtk.vtkRenderWindow()
  win.AddRenderer(ren)
  iren = vtk.vtkRenderWindowInteractor()
  iren.SetRenderWindow(win)
  ren.AddActor(actor)
  win.SetSize(1024,512)

  def update_callback(caller:vtk.vtkObject, event_id:int):
    # NOTE: do this to release python GIL lock
    time.sleep(0)

  # iren.AddObserver("TimerEvent", update_callback)
  iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
  iren.Initialize()
  # timer_id = iren.CreateRepeatingTimer(1)
  # iren.Start()

  last_mtime = 0
  while not stop_evt.is_set():
    try:
      with lck:
        iren.ProcessEvents()
        m_time = mapper.GetMTime()
        # FIXME: this will cause crashing
        if m_time > last_mtime:win.Render()
        last_mtime = m_time
        # NOTE: do this to release python GIL lock
        time.sleep(0)
        # iren.Start()
        # iren.DestroyTimer(timer_id)
    except Exception as e:
      print(e)

async def handle_message(websocket: ServerConnection):
  reader = vtk.vtkXMLPolyDataReader()
  reader.ReadFromInputStringOn()
  while not stop_evt.is_set():
    try:
      raw = await websocket.recv(decode=False)
    except ConnectionClosedOK:
      return

    message = ForwardMessage.GetRootAs(raw, 0)
    timestamp = message.Timestamp()
    print(f"message cost {(time.perf_counter()*1000-timestamp):.4}ms")
    n_informations = message.InformationsLength()
    assert n_informations == 1
    information = message.Informations(0)
    print(information.TotalFrameCount())
    print(information.TotalFrameDuration())
    data_object = information.DataObject()
    xml = data_object.Xml()
    assert isinstance(xml, bytes)
    # NOTE(k): we have to this lock, otherwise vtk could crash
    # seem like we can't call vtk in another thread
    with lck:
      reader.SetInputString(xml.decode("utf8"))
      reader.Update()
      poly: vtk.vtkPolyData = reader.GetOutput(0)
      assert isinstance(poly, vtk.vtkPolyData)
      # attr = poly.GetPointData()
      mapper.SetInputData(reader.GetOutput(0))
      mapper.Modified()

def message_worker():
  host = "localhost"
  port = 8080

  async def start():
    async with serve(handle_message, host, port, max_size=None) as server:
      print(f"Listening on {host}:{port}")
      await server.serve_forever()
  asyncio.run(start())

def main():
  t1 = Thread(target=message_worker, daemon=True)
  t2 = Thread(target=render_worker, daemon=True)

  workers = [t1, t2]
  for worker in workers: worker.start()
  try:
    for worker in workers:worker.join()
  except KeyboardInterrupt:
    stop_evt.set()
    import sys
    sys.exit(0)

if __name__ == "__main__":
  main()