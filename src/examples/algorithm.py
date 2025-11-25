# Ref: https://www.kitware.com/vtkpythonalgorithm-is-great/

import vtk
from vtk.util import keys
from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase
from dataclasses import dataclass
import typing as t

class MyAlgorithm:
  def Initialize(self, vtkself):
    vtkself.SetNumberOfInputPorts(1)
    vtkself.SetNumberOfOutputPorts(1)

  # These methods are called once for each input and output port
  def FillInputPortInformation(self, vtkself, port, info):
    info.Set(vtk.vtkAlgorithm.INPUT_REQUIRED_DATA_TYPE(), "vtkDataSet")
    return 1

  def FillOutputPortInformation(self, vtkself, port, info):
    # If the output DATA_TYPE_NAME() is a concrete class name
    # the pipeline (executive) will create the output data object for the port automatically before the filter executes
    # if it is the name of an abstract class, it is the developer's responsibility to create the output data object later
    info.Set(vtk.vtkDataObject.DATA_TYPE_NAME(), "vtkPolyData")
    return 1

  def ProcessRequest(self, vtkself, request, inInfo, outInfo):
    # REQUEST_DATA_OBJECT(): create your output data object(s)
    # REQUEST_INFORMATION(): provide meta-data for downstream
    # REQUEST_UPDATE_EXTENT(): modify any data coming from downstream or create a data request (for sinks)
    # REQUEST_DATA(): do your thing. Take input data(if any), do something with it, produce output data (if any)
    if request.Has(vtk.vtkDemandDrivenPipeline.REQUEST_DATA()):
      self.RequestData(vtkself, request, inInfo, outInfo)
    return 1

  def RequestData(self, vtkself, request, inInfo, outInfo):
    # input data
    inp = inInfo[0].GetInformationObject(0).Get(vtk.vtkDataObject.DATA_OBJECT())
    opt = outInfo.GetInformationObject(0).Get(vtk.vtkDataObject.DATA_OBJECT())

    # simplfied version
    # inp = vtk.vtkDataSet.GetData(inInfo[0])
    # opt = vtk.vtkDataSet.GetData(outInfo)

    # FIXME: add this to the ue demo
    cf = vtk.vtkContourFilter()
    cf.SetInputData(inp)
    cf.SetValue(0,200)

    # FIXME: check it later, maybe usefull to reduce the size of FEM meshes
    sf = vtk.vtkShrinkPolyData()
    sf.SetInputConnection(cf.GetOutputPort(0))
    sf.Update()

    opt.ShallowCopy(sf.GetOutput(0))
    return 1

class ContourShrink(VTKPythonAlgorithmBase):
  def __init__(self):
    VTKPythonAlgorithmBase.__init__(
      self,
      nInputPorts=1,
      nOutputPorts=1,
      inputType="vtkDataSet",
      outputType="vtkPolyData"
    )
    # VTKPythonAlgorithmBase.__init__(self)

  # def RequestInformation(self, request, inInfo, outInfo) -> int:
  #   return 1

  def RequestData(self, request, inInfo, outInfo):
    # inp = vtk.vtkDataSet.GetData(inInfo[0])
    # opt = vtk.vtkDataSet.GetData(outInfo)

    inp = vtk.vtkDataSet.GetData(inInfo[0], 0)
    opt = vtk.vtkDataSet.GetData(outInfo, 0)

    cf = vtk.vtkContourFilter()
    cf.SetInputData(inp)
    cf.SetValue(0,200)

    sf = vtk.vtkShrinkPolyData()
    sf.SetInputConnection(cf.GetOutputPort(0))
    sf.Update()

    opt.ShallowCopy(sf.GetOutput(0))
    return 1

def main():
  # the order of passes(3) (order of execution)
  # 1. RequestDataObject                   (upstream -> downstream)
  # 2. RequestInformation(meta-data pass)  (upstream -> downstream)
  # 3. RequestUpdateExtent                 (downstream -> upstream)
  # 4. RequestData                         (upstream -> downstream)

  w = vtk.vtkRTAnalyticSource()

  # pa = vtk.vtkPythonAlgorithm()
  # pa.SetPythonObject(MyAlgorithm())
  # pa.SetInputConnection(w.GetOutputPort())
  # pa.Update()

  pa = ContourShrink()
  pa.SetInputConnection(w.GetOutputPort())
  pa.Update()
  print(pa.GetOutputDataObject(0).GetClassName())
  print(pa.GetOutputDataObject(0).GetNumberOfCells())

if __name__ == "__main__":
  main()
