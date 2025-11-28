import vtk
from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase

class MySource(VTKPythonAlgorithmBase):
  def __init__(self):
    VTKPythonAlgorithmBase.__init__(self,
      nInputPorts=0,
      nOutputPorts=1, outputType='vtkPolyData')

  def RequestInformation(self, request, inInfo, outInfo):
    print("MySource RequestInformation:")
    # print outInfo.GetInformationObject(0)
    out = outInfo.GetInformationObject(0)

    time_steps = [0.0, 1.0, 2.0, 3.0]
    out.Set(vtk.vtkStreamingDemandDrivenPipeline.TIME_STEPS(), time_steps, 4)
    time_range = [0.0, 3.0]
    out.Set(vtk.vtkStreamingDemandDrivenPipeline.TIME_RANGE(), time_range, 2)
    return 1

  def RequestUpdateExtent(self, request, inInfo, outInfo):
    print("MySource RequestUpdateExtent:")
    #print outInfo.GetInformationObject(0)
    # NOTE: UPDATE_TIME_STEP() is not a request key
    # print(f"Request Has UPDATE_TIME_STEP: {request.Has(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP())}")
    out = outInfo.GetInformationObject(0)
    print(f"OutputPort Has UPDATE_TIME_STEP: {out.Get(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP())}")
    return 1

  def RequestData(self, request, inInfo, outInfo):
    print("MySource RequestData:")
    # print outInfo.GetInformationObject(0)
    return 1

class MyFilter(VTKPythonAlgorithmBase):
  def __init__(self):
    VTKPythonAlgorithmBase.__init__(self,
      nInputPorts=1, inputType='vtkPolyData',
      nOutputPorts=1, outputType='vtkPolyData')

  def RequestInformation(self, request, inInfo, outInfo):
    print("MyFilter RequestInformation:")
    # print outInfo.GetInformationObject(0)
    return 1

  def RequestUpdateExtent(self, request, inInfo, outInfo):
    print("MyFilter RequestUpdateExtent:")
    # print outInfo.GetInformationObject(0)
    return 1

  def RequestData(self, request, inInfo, outInfo):
    print("MyFilter RequestData:")
    # print outInfo.GetInformationObject(0)
    return 1

def main():
  s = MySource()
  f = MyFilter()
  f.SetInputConnection(s.GetOutputPort())
  print("## Pass 1 ##")
  f.Update()
  print()

  print("## Pass 2 ##")
  f.Update()
  print()

  print("## Pass 3 ##")
  f.Modified()
  f.Update()
  print()

  print("## Pass 4 ##")
  in_info = f.GetInputInformation(0,0);
  in_info.Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), 2.0)
  f.Modified()
  f.Update()

  print()
  print("## Pass 5 ##")
  in_info = f.GetInputInformation(0,0);
  in_info.Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), 2.0)
  f.Modified()
  f.Update()

  print()
  print("## Pass 6 ##")
  # NOTE: even UPDATE_TIME_STEP() is not a request key, this also work
  # NOTE: RequestInformation will only be fired if algo is Modified, it's kind a black box, we should read more vtk source code
  req = vtk.vtkInformation()
  req.Set(vtk.vtkStreamingDemandDrivenPipeline.UPDATE_TIME_STEP(), 4.0)
  f.Modified()
  f.Update(req)
  # f.Update()
  # f.UpdateExtent()
  # f.Modified()
  # f.PropagateUpdateExtent()

if __name__ == "__main__":
  main()
