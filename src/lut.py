import vtk
import matplotlib.cm as cm
import random
from dataclasses import dataclass

def lut_from_name(cmap_name:str, n=512) -> vtk.vtkLookupTable:
  cmap = cm.get_cmap(cmap_name, n)
  lut = vtk.vtkLookupTable()
  lut.SetNumberOfTableValues(n)
  for i in range(n):
    r,g,b,a = cmap(i/(n-1))
    lut.SetTableValue(i, r,g,b,a)
  lut.Build()
  return lut

def apply_lut(mesh:vtk.vtkPolyData, lut:vtk.vtkLookupTable, scalar:str|None = None) -> int:
  point_data = mesh.GetPointData()
  array:vtk.vtkFloatArray
  if scalar:
    array = point_data.GetScalars(scalar)
  else:
    array = point_data.GetScalars()

  if not array: return 0
  # rng = array.GetRange()
  # lut.SetTableRange(rng)
  # color_array = lut.MapScalars(array, vtk.VTK_COLOR_MODE_DEFAULT, -1)
  # color_array.SetName("Colors")
  # point_data.AddArray(color_array)
  ## point_data.SetScalars(color_array)
  # return 1 

#   color_array = vtk.vtkUnsignedCharArray()
#   color_array.SetNumberOfComponents(3)
#   color_array.SetName("Colors")
#   for i in range(array.GetNumberOfTuples()):
#     value = array.GetValue(i)
#     color = random.randint(0,255)
#     color_array.InsertNextTuple3(color,color,color)
#   point_data.AddArray(color_array)
#   point_data.SetScalars(color_array)

  if array:
    ret = 1
    color_array = vtk.vtkUnsignedCharArray()
    color_array.SetNumberOfComponents(3)
    color_array.SetName("Colors")

    value_rng = lut.GetValueRange()
    value_dim = value_rng[1]-value_rng[0]
    color_count:int = lut.GetNumberOfColors()
    for i in range(array.GetNumberOfTuples()):
      value = array.GetValue(i)
      normalized_value = ((value-value_rng[0])/value_dim)
      color_index = int(normalized_value*(color_count-1))
      color = lut.GetTableValue(color_index)
      # color_array.InsertNextTuple3(0,255,0)
      color_array.InsertNextTuple3(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255))
    # mesh.GetFieldData().AddArray(color_array)
    point_data.AddArray(color_array)
    # point_data.SetScalars(color_array)

def default_lut(rng:tuple[int,int], table_size=256) -> vtk.vtkLookupTable:
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
  return lut

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