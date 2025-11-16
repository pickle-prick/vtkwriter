# Ref: https://www.kitware.com/a-vtk-pipeline-primer-part-2/
# Ref: https://www.kitware.com/a-vtk-pipeline-primer-part-3/

import vtk
from vtk.util import keys
from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase
from dataclasses import dataclass
import typing as t

metaDataKey = keys.MakeKey(keys.DataObjectMetaDataKey, "a meta-data", "my module")
requestKey = keys.MakeKey(keys.IntegerRequestKey, "a request", "my module")

class MySource(VTKPythonAlgorithmBase):
  def __init__(self):
    VTKPythonAlgorithmBase.__init__(
      self,
      nInputPorts=0,
      nOutputPorts=1,
      outputType="vtkPolyData"
    )

  def RequestInformation(self, request, inInfo, outInfo) -> int:
    outInfo.GetInformationObject(0).Set(metaDataKey, vtk.vtkPolyData())
    return 1

  def RequestUpdateExtent(self, request, inInfo, outInfo) -> int:
    print(outInfo.GetInformationObject(0))
    return 1

  def RequestData(self, request, inInfo, outInfo) -> int:
    outInfo0 = outInfo.GetInformationObject(0)
    areq = outInfo0.Get(requestKey)
    s = vtk.vtkSphereSource()
    s.SetRadius(areq)
    s.Update()
    output = outInfo0.Get(vtk.vtkDataObject.DATA_OBJECT())
    output.ShallowCopy(s.GetOutput())
    return 1

  def RequestDataObject(self, request, inInfo, outInfo) -> int:
    return 1

class MyFilter(VTKPythonAlgorithmBase):
  def __init__(self):
    VTKPythonAlgorithmBase.__init__(
      self,
      nInputPorts=1,
      nOutputPorts=1,
      outputType="vtkPolyData"
    )

  def RequestInformation(self, request, inInfo, outInfo) -> int:
    metaData = inInfo[0].GetInformationObject(0).Get(metaDataKey)
    newMetaData = metaData.NewInstance()
    newMetaData.ShallowCopy(metaData)
    someArray = vtk.vtkCharArray()
    someArray.SetName("someArray")
    newMetaData.GetFieldData().AddArray(someArray)
    outInfo.GetInformationObject(0).Set(metaDataKey, newMetaData)

    # print(outInfo.GetInformationObject(0))
    return 1

  def RequestUpdateExtent(self, request, inInfo, outInfo) -> int:
    print(outInfo.GetInformationObject(0))
    areq = outInfo.GetInformationObject(0).Get(requestKey)
    inInfo[0].GetInformationObject(0).Set(requestKey, areq+1)
    return 1

  def RequestData(self, request, inInfo, outInfo) -> int:
    inInfo0 = inInfo[0].GetInformationObject(0)
    outInfo0 = outInfo.GetInformationObject(0)
    input = inInfo0.Get(vtk.vtkDataObject.DATA_OBJECT())
    output = outInfo0.Get(vtk.vtkDataObject.DATA_OBJECT())
    sh = vtk.vtkShrinkPolyData()
    sh.SetInputData(input)
    sh.Update()
    output.ShallowCopy(sh.GetOutput())
    return 1

  def RequestDataObject(self, request, inInfo, outInfo) -> int:
    return 1

def main():
  # the order of passes(3) (order of execution)
  # 1. RequestDataObject                   (upstream -> downstream)
  # 2. RequestInformation(meta-data pass)  (upstream -> downstream)
  # 3. RequestUpdateExtent                 (downstream -> upstream)
  # 4. RequestData                         (upstream -> downstream)
  
  s = MySource()
  f = MyFilter()
  # print(f"source: {s}")
  # print(f"filter: {f}")
  f.SetInputConnection(s.GetOutputPort(0))
  # f.Update()
  # f.UpdateInformation()
  # s.Modified()
  f.UpdateInformation()
  outInfo = f.GetOutputInformation(0)
  outInfo.Set(requestKey, 0)
  f.PropagateUpdateExtent()

if __name__ == "__main__":
  main()
