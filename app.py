from flask import Flask, request, redirect, url_for, send_file, render_template, jsonify
import json
import requests
import rhino3dm as rh
import base64

app = Flask(__name__, static_url_path='/static')


@app.route('/', methods=['GET', 'POST'])
def index():
    return render_template('index.html')


@app.route("/update_variables", methods=["POST"])
def update_variables():
    if request.form.get("startMonth"):
        global start_m
        start_m = int(request.form.get("startMonth"))
    if request.form.get("startDay"):
        global start_d
        start_d = int(request.form.get("startDay"))
    if request.form.get("startHour"):
        global start_h
        start_h = int(request.form.get("startHour"))
    if request.form.get("endMonth"):
        global end_m
        end_m = int(request.form.get("endMonth"))
    if request.form.get("endDay"):
        global end_d
        end_d = int(request.form.get("endDay"))
    if request.form.get("endHour"):
        global end_h
        end_h = int(request.form.get("endHour"))
    return redirect(request.referrer)


@app.route('/process', methods=['POST'])
def process():
    if uploaded_file := request.files['file']:
        uploaded_file.save('uploaded_file.3dm')
        update_variables()
        total_sunlight_hours, total_radiation_hours = run_sunlight_analysis('uploaded_file.3dm', start_m,
                              start_d, start_h, end_m, end_d, end_h)
        return render_template('index.html', total_sunlight_hours=total_sunlight_hours, total_radiation_hours=total_radiation_hours)
    return redirect(url_for('index'))

@app.route('/process', methods=['GET'])
def process_get():
    return redirect(url_for('index'))

def run_sunlight_analysis(uploaded_file, start_m, start_d, start_h, end_m, end_d, end_h):
    total_sunlight_hours = None
    total_radiation_hours = None
    compute_url = "http://localhost:6500/"

    class __Rhino3dmEncoder(json.JSONEncoder):
        def default(self, o):
            if hasattr(o, "Encode"):
                return o.Encode()
            return json.JSONEncoder.default(self, o)

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

    context_breps = [obj.Geometry for obj in context_list]

    geometry_breps = [obj.Geometry for obj in geometry_list]

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

    geometry_list = [
        {
            "ParamName": "geo",
            "InnerTree": {
                f"{{ {i}; }}": [{"type": "Rhino.Geometry.Brep", "data": brep}]
            },
        }
        for i, brep in enumerate(serialized_geometry)
    ]
    epw_dict = {
        "ParamName": "epw",
        "InnerTree": {
            "{ 0; }": [
                {
                    "type": "System.String",
                    "data": "C:/Users/RivinduB/Desktop/EA_Tool/AUS_NSW_Sydney.Obs-Obsservatory.Hill.947680_TMYx.epw"
                }
            ]
        }
    }

    start_m_dict = {
        "ParamName": "Start_M",
        "InnerTree": {
            "{ 0; }": [
                {
                    "type": "System.Int32",
                    "data": start_m
                }
            ]
        }
    }

    start_d_dict = {
        "ParamName": "Start_D",
        "InnerTree": {
            "{ 0; }": [
                {
                    "type": "System.Int32",
                    "data": start_d
                }
            ]
        }
    }

    start_h_dict = {
        "ParamName": "Start_H",
        "InnerTree": {
            "{ 0; }": [
                {
                    "type": "System.Int32",
                    "data": start_h
                }
            ]
        }
    }

    end_m_dict = {
        "ParamName": "End_M",
        "InnerTree": {
            "{ 0; }": [
                {
                    "type": "System.Int32",
                    "data": end_m
                }
            ]
        }
    }

    end_d_dict = {
        "ParamName": "End_D",
        "InnerTree": {
            "{ 0; }": [
                {
                    "type": "System.Int32",
                    "data": end_d
                }
            ]
        }
    }

    end_h_dict = {
        "ParamName": "End_H",
        "InnerTree": {
            "{ 0; }": [
                {
                    "type": "System.Int32",
                    "data": end_h
                }
            ]
        }
    }

    gh_sunlight = open(r"./sunlight.ghx", mode="r",
                       encoding="utf-8-sig").read()
    gh_sunlight_bytes = gh_sunlight.encode("utf-8")
    gh_sunlight_encoded = base64.b64encode(gh_sunlight_bytes)
    gh_sunlight_decoded = gh_sunlight_encoded.decode("utf-8")

    geo_payload = {
        "algo": gh_sunlight_decoded,
        "pointer": None,
        "values": context_list + geometry_list + [epw_dict] + [start_m_dict] + [start_d_dict] + [start_h_dict] + [end_m_dict] + [end_d_dict] + [end_h_dict]
    }

    res = requests.post(f"{compute_url}grasshopper", json=geo_payload)
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
        elif paramName == "RH_OUT:radiation":
            innerTree = val['InnerTree']
            for key, innerVals in innerTree.items():
                for innerVal in innerVals:
                    if 'data' in innerVal:
                        data = json.loads(innerVal['data'])
                        geo = rh.CommonObject.Decode(data)
                        att = rh.ObjectAttributes()
                        att.LayerIndex = radiation_layerIndex
                        new_rhFile.Objects.AddMesh(geo, att)
        elif paramName == "RH_OUT:total_radiation":
            innerTree = val['InnerTree']
            for key, innerVals in innerTree.items():
                for innerVal in innerVals:
                    if 'data' in innerVal:
                        total_radiation_hours = round(float(json.loads(innerVal['data'])), 2)
        elif paramName == "RH_OUT:total_sunlight":
            innerTree = val['InnerTree']
            for key, innerVals in innerTree.items():
                for innerVal in innerVals:
                    if 'data' in innerVal:
                        total_sunlight_hours = round(float(json.loads(innerVal['data'])), 2)
    new_rhFile.Write("./static/sunlight.3dm")
    return total_sunlight_hours, total_radiation_hours

if __name__ == '__main__':
    app.run(host ='0.0.0.0', port=5000)
