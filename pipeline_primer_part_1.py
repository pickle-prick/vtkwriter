import vtk
from vtk.util import keys
from vtk.util.vtkAlgorithm import VTKPythonAlgorithmBase
from dataclasses import dataclass
import typing as t

class Source(VTKPythonAlgorithmBase):
  def __init__(self):
    VTKPythonAlgorithmBase.__init__(self, nInputPorts=0, nOutputPorts=1, outputType="vtkPolyData")

  def RequestData(self, request, inInfo, outInfo):
    info = outInfo.GetInformationObject(0)
    output = vtk.vtkPolyData.GetData(info)
    # print(info)
    return 1

class Filter0(VTKPythonAlgorithmBase):
  def __init__(self):
    VTKPythonAlgorithmBase.__init__(self, nInputPorts=2, nOutputPorts=2, outputType="vtkPolyData")

  def RequestInformation(self, request, inInfo, outInfo):
    inPort0 = inInfo[0]
    return 1

  def FillInputPortInformation(self, port, info):
    if port == 0:
      # FIXME: should this info be a informationVector?
      info.Set(vtk.vtkAlgorithm.INPUT_IS_REPEATABLE(), 1)
    return 1

  def RequestData(self, request, inInfo, outInfo):
    print(inInfo[0], inInfo[1])
    info = inInfo[0].GetInformationObject(0)
    input = vtk.vtkPolyData.GetData(info)
    info = outInfo.GetInformationObject(0)
    output = vtk.vtkPolyData.GetData(info)
    return 1

class Filter1(VTKPythonAlgorithmBase):
  def __init__(self):
    VTKPythonAlgorithmBase.__init__(self, nInputPorts=1, nOutputPorts=1, outputType="vtkPolyData")

  def RequestData(self, request, inInfo, outInfo):
    info = inInfo[0].GetInformationObject(0)
    intput = vtk.vtkPolyData.GetData(info)
    info = outInfo.GetInformationObject(0)
    output = vtk.vtkPolyData.GetData(info) # output object/container, we do shallowCopy when producing output
    return 1

class Filter2(VTKPythonAlgorithmBase):
  def __init__(self):
    VTKPythonAlgorithmBase.__init__(self, nInputPorts=1, nOutputPorts=1, outputType="vtkPolyData")

  def RequestData(self, request, inInfo, outInfo):
    info = inInfo[0].GetInformationObject(0)
    intput = vtk.vtkPolyData.GetData(info)
    info = outInfo.GetInformationObejct(0)
    output = vtk.vtkPolyData.GetData(info) # output object/container, we do shallowCopy when producing output
    return 1

def main():
  # key = keys.MakeKey(keys.ObjectBaseKey, "a new key", "some class")
  # print(key)

  # info = vtk.vtkInformation()
  # print(info)

  # # still worked, but looks backwards
  # # key.Set(info, vtk.vtkObject())
  # info.Set(key, vtk.vtkObject())
  # print(f"info after set: {info}")

  s0 = Source()
  s1 = Source()
  s2 = Source()

  f0 = Filter0()
  f0.AddInputConnection(0, s0.GetOutputPort())
  f0.AddInputConnection(0, s1.GetOutputPort())
  f0.SetInputConnection(1, s2.GetOutputPort())

  f1 = Filter1()
  f1.SetInputConnection(f0.GetOutputPort(0))

  f2 = Filter2()
  f2.SetInputConnection(f0.GetOutputPort(1))

  f1.Update()

if __name__ == "__main__":
  main()
