from flask import Flask, request, redirect, url_for, send_file, render_template, jsonify
import json
import requests
import rhino3dm as rh
import base64

compute_url = "http://13.54.229.195:80/"

headers = {
    "RhinoComputeKey": "8c96f7d9-5a62-4bbf-ad3f-6e976b94ea1e"
}

class __Rhino3dmEncoder(json.JSONEncoder):
    def default(self, o):
        if hasattr(o, "Encode"):
            return o.Encode()
        return json.JSONEncoder.default(self, o)

uploaded_file = './uploaded_file.3dm'
rhFile = rh.File3dm.Read(uploaded_file)
layers = rhFile.Layers
context_list = []
geometry_list = []
for obj in rhFile.Objects:
    layer_index = obj.Attributes.LayerIndex
    if layers[layer_index].Name == "Buildings":
        context_list.append(obj)
    elif layers[layer_index].Name == "Geometry":
        geometry_list.append(obj)

context_breps = [obj.Geometry for obj in context_list if isinstance(
    obj.Geometry, rh.Extrusion)]

geometry_breps = [obj.Geometry for obj in geometry_list if isinstance(
    obj.Geometry, rh.Extrusion)]

serialized_context = []
for brep in context_breps:
    serialized_brep = json.dumps(brep, cls=__Rhino3dmEncoder)
    serialized_context.append(serialized_brep)

serialized_geometry = []
for brep in geometry_breps:
    serialized_brep = json.dumps(brep, cls=__Rhino3dmEncoder)
    serialized_geometry.append(serialized_brep)

context_list = [{"ParamName": "context", "InnerTree": {}}]
for i, brep_context in enumerate(serialized_context):
    key = f"{{{i};0}}"
    value = [
        {
            "type": "Rhino.Geometry.Brep",
            "data": brep_context
        }
    ]
    context_list[0]["InnerTree"][key] = value

geometry_list = [{"ParamName": "geo", "InnerTree": {}}]
for i, geometry in enumerate(serialized_geometry):
    key = f"{{{i};0}}"
    value = [
        {
            "type": "Rhino.Geometry.Brep",
            "data": geometry
        }
    ]
    geometry_list[0]["InnerTree"][key] = value


gh_sunlight = open(r"./test_sunlight.ghx", mode="r",
                   encoding="utf-8-sig").read()
gh_sunlight_bytes = gh_sunlight.encode("utf-8")
gh_sunlight_encoded = base64.b64encode(gh_sunlight_bytes)
gh_sunlight_decoded = gh_sunlight_encoded.decode("utf-8")

geo_payload = {
    "algo": gh_sunlight_decoded,
    "pointer": None,
    "values": context_list + geometry_list
}

res = requests.post(
    f"{compute_url}grasshopper", json=geo_payload, headers=headers
)

response_object = json.loads(res.content)['values']

new_rhFile = rh.File3dm.Read(uploaded_file)
sunlight_layer = rh.Layer()
sunlight_layer.Name = "Sunlight"
sunlight_layerIndex = new_rhFile.Layers.Add(sunlight_layer)

radiation_layer = rh.Layer()
radiation_layer.Name = "Radiation"
radiation_layerIndex = new_rhFile.Layers.Add(radiation_layer)

for val in response_object:
    paramName = val['ParamName']
    if paramName == 'RH_OUT:mesh':
        innerTree = val['InnerTree']
        for key, innerVals in innerTree.items():
            for innerVal in innerVals:
                if 'data' in innerVal:
                    data = json.loads(innerVal['data'])
                    geo = rh.CommonObject.Decode(data)
                    att = rh.ObjectAttributes()
                    att.LayerIndex = sunlight_layerIndex
                    new_rhFile.Objects.AddMesh(geo, att)
    elif paramName == "RH_OUT:total_sunlight":
        innerTree = val['InnerTree']
        for key, innerVals in innerTree.items():
            for innerVal in innerVals:
                if 'data' in innerVal:
                    total_sunlight_hours = round(float(json.loads(innerVal['data'])), 2)
new_rhFile.Write("./static/sunlight.3dm")
