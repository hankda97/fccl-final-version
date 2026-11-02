"""Fixed interface payload only: no simulator, RNG, plant connection or I/O."""
from copy import deepcopy
from c_dashboard.data.schema import FEATURE_UNITS
from c_dashboard.data.fixtures import load_mock_fixture
from c_dashboard.workspace_modes.ports import Capability, SCHEMA_VERSION

EARLY='2026-11-01T08:00:00+08:00'
LATE='2026-11-01T08:00:10+08:00'


def payload(context):
    features={name:float(load_mock_fixture('normal').frame.iloc[0][name]) for name in FEATURE_UNITS}
    def row(record_id,values,units,**kwargs):
        return dict(record_id=record_id,station='lamination',product_batch='SAME-BATCH',root_roll_id='SAME-ROLL',
            timestamp=EARLY,available_at=EARLY,material_md_start_m=0.,material_md_end_m=1.,values=values,
            units=units,field_available_at={k:EARLY for k in values},availability={k:True for k in values},**kwargs)
    event=row('same-id',{'line_speed_m_min':-.2},{'line_speed_m_min':'m/min'},confirmed=True,event_type='confirmed_simulation')
    event['parameter_diff']=event.pop('values')
    measurement=row('measurement',{'peel_strength_n_mm':1.3,'heat_resistance_c':280.},
                    {'peel_strength_n_mm':'N/mm','heat_resistance_c':'°C'})
    measurement['field_available_at']['heat_resistance_c']=LATE
    return dict(mode_id=context.mode_id,workspace_id=context.workspace_id,run_id=context.run_id,
        generation=context.generation,schema_version=SCHEMA_VERSION,source_kind='Synthetic',
        source_id='fixed-render-test',simulator_id='interface-test-only',simulator_version='test-v1',
        seed=42,config_version='test-config-v1',store_id='memory-only',events=[event],
        process=[row('process',features,dict(FEATURE_UNITS))],measurement=[measurement],
        raw_signal=[row('raw',{'laser_signal':10.},{'laser_signal':'test-unit'})],
        processed_signal=[row('filtered',{'laser_signal':9.},{'laser_signal':'test-unit'})],
        truth=[row('latent',{'noise_cause':99.},{'noise_cause':'test-unit'})],
        prediction=[row('pred',{'peel_strength_n_mm':1.9},{'peel_strength_n_mm':'N/mm'})])


class FixedInterfaceProvider:
    """Injected by tests only; never imported into the application composition."""
    def __init__(self,context):
        self.context=context
        self.fixed=payload(context)
    def describe(self):
        return Capability(self.context.mode_id,True,'interface-test-v1',actions=('inspect',),reason='固定介面測試，非完整模擬器')
    def inspect(self):
        return deepcopy(self.fixed)
