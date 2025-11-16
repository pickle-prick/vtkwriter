import vtk
import asyncio
import websockets
import pyvista as pv

async def main():
  uri = "ws://localhost:1080"

  pl = pv.Plotter()
  pl.show(auto_close=False, interactive_update=True)
  mesh_actor = None
  async with websockets.connect(uri, max_size=None) as ws:
    while True:
      mesh_bytes = await ws.recv()
      print(f"Received mesh: {len(mesh_bytes)} byts")
      # print(mesh_bytes[:100])

      ## legacy reader
      # reader = vtk.vtkPolyDataReader()
      # reader.ReadFromInputStringOn()
      # reader.SetInputString(mesh_bytes)
      # reader.Update()

      ## XML reader
      reader = vtk.vtkXMLPolyDataReader()
      reader.ReadFromInputStringOn()
      reader.SetInputString(mesh_bytes)
      reader.Update()

      polydata = reader.GetOutput()
      pv_mesh = pv.wrap(polydata)

      if mesh_actor is None:
        mesh_actor = pl.add_mesh(pv_mesh, scalars="Colors", rgb=True, show_edges=False)
        # mesh_actor = pl.add_mesh(pv_mesh, show_edges=True)
      else:
        mesh_actor.mapper.SetInputData(pv_mesh)
        mesh_actor.mapper.Update()

      pl.update()
      await asyncio.sleep(0.0)

if __name__ == "__main__":
  asyncio.run(main())
