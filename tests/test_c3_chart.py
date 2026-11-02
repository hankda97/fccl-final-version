from dataclasses import replace

from c_dashboard.spc.baseline import build_baseline
from c_dashboard.spc.service import compute_spc
from c_dashboard.spc.types import SourceContext
from c_dashboard.ui.spc_panel import chart_spec
from c3_support import MD, PEEL, hand_history, monitoring


def result(means):
    history,p=hand_history()
    rows,_=monitoring(means)
    return rows,SourceContext("test",p),build_baseline(history,p)


def test_chart_layers_preserve_raw_points_means_limits_and_negative_dimensions():
    rows,c,b=result([1.25,.5,1.25])
    r=compute_spc(rows,c,b)
    spec=chart_spec(r,PEEL)
    assert len(spec["layer"][0]["data"]["values"])==15
    assert len(spec["layer"][1]["data"]["values"])==3
    lines={layer["data"]["values"][0]["series"]:layer["data"]["values"][0]["value"]
           for layer in spec["layer"] if layer["mark"]["type"]=="rule"}
    assert lines=={"CL":b.target(PEEL).cl,"UCL":b.target(PEEL).ucl,"LCL":b.target(PEEL).lcl}
    assert spec["layer"][-1]["data"]["values"][0]["id"]==r.events[0].event_id
    dim=chart_spec(r,MD)
    assert all(x["value"]<0 for x in dim["layer"][0]["data"]["values"])
    assert dim["layer"][0]["encoding"]["y"]["scale"]["zero"] is False


def test_invalid_group_creates_line_break_and_no_baseline_has_no_control_rules():
    rows,c,b=result([1.25]*3)
    rows.loc[5,PEEL]=float("nan")
    spec=chart_spec(compute_spc(rows,c,b),PEEL)
    means=spec["layer"][1]["data"]["values"]
    assert len(means)==2 and means[0]["line_segment"]!=means[1]["line_segment"]
    no_baseline=chart_spec(compute_spc(rows,c,None),PEEL)
    assert not any(layer["mark"]["type"]=="rule" for layer in no_baseline["layer"])
    assert no_baseline["layer"][0]["data"]["values"]  # Raw measurement remains useful.
    all_incomplete=chart_spec(compute_spc(rows.iloc[:3],c,b),PEEL)
    assert not any(layer["mark"]["type"]=="rule" for layer in all_incomplete["layer"])
