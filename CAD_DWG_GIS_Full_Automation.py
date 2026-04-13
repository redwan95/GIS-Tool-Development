import arcpy
import os
import sys
import re
import ipywidgets as widgets
from IPython.display import display
from datetime import datetime

# ============================================================
# CONFIG — DEFAULT PATHS (all configurable via UI widgets)
# ============================================================
DEFAULT_DWG_FOLDER = r"C:\Users\kabirr\OneDrive - Missouri Department of Conservation\Desktop\86-12-12\Civil"
DEFAULT_QC_GDB = r"N:\EIAMS\GIS\Project_Map_Docs\IAM_QA_QC_ArcGIS_Pro_Project\IAM_QA_QC.gdb"
DEFAULT_SDE_WS = r"N:\EIAMS\GIS\Project_Map_Docs\IAM_QA_QC_ArcGIS_Pro_Project\GIS_Production@sde2_GIS_VIEWER.sde\PRODUCTION.IT.Infrastructure"

arcpy.env.overwriteOutput = True

# ============================================================
# GLOBALS
# ============================================================
CURRENT_DWG = None
SESSION_HISTORY = []
SESSION_LOG_LINES = []
PH = "── Select ──"
ALL_LYR = "── ALL LAYERS (entire feature type) ──"


def log(msg, level="INFO"):
    """Timestamped log to output widget + stored for file export"""
    ts = datetime.now().strftime("%H:%M:%S")
    icons = {
        "INFO": "ℹ️", "SUCCESS": "✅", "OK": "✅",
        "WARNING": "⚠️", "WARN": "⚠️",
        "ERROR": "❌", "ERR": "❌",
        "DETAIL": "📋", "DATA": "📊",
    }
    line = f"[{ts}] {icons.get(level, 'ℹ️')} {msg}"
    SESSION_LOG_LINES.append(line)
    print(line)


def is_real(dd):
    """True if dropdown has a real selection (not placeholder)"""
    v = dd.value
    return v is not None and v != PH and not str(v).startswith("── Select")


def is_all_layers():
    """True if user selected ALL LAYERS option"""
    return w_layer.value == ALL_LYR


def make_gdb_name(project_number):
    """
    Create GDB name preserving the project number exactly.
    Input:  86-12-12  →  Output: Project_86-12-12_temp.gdb
    Input:  86121200  →  Output: Project_86121200_temp.gdb
    
    Hyphens are VALID in file/folder names (GDB is just a folder).
    Only strips characters that are truly illegal in Windows paths.
    """
    # Remove only characters illegal in Windows filenames: \ / : * ? " < > |
    cleaned = re.sub(r'[\\/:*?"<>|]', '', project_number.strip())
    # Remove leading/trailing spaces and dots (Windows restriction)
    cleaned = cleaned.strip('. ')
    if not cleaned:
        cleaned = "UNKNOWN"
    return f"Project_{cleaned}_temp.gdb"


def make_fc_name(text):
    """Make a string safe for feature class naming inside a GDB"""
    s = re.sub(r'[^a-zA-Z0-9_]', '_', text.strip())
    # FC names can't start with a number
    if s and s[0].isdigit():
        s = 'DWG_' + s
    # Remove consecutive underscores
    s = re.sub(r'_+', '_', s).strip('_')
    return s or "Untitled"


# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def scan_dwg_folder(folder_path):
    """Return sorted list of .dwg filenames in folder"""
    if not os.path.exists(folder_path):
        return []
    return sorted(f for f in os.listdir(folder_path) if f.lower().endswith(".dwg"))


def load_sde_targets(sde_path):
    """List feature classes from SDE using 4 fallback methods"""
    if not arcpy.Exists(sde_path):
        return [], f"Path does not exist: {sde_path}"

    saved_ws = arcpy.env.workspace

    # Method 1: Direct
    try:
        arcpy.env.workspace = sde_path
        fcs = arcpy.ListFeatureClasses() or []
        arcpy.env.workspace = saved_ws
        if fcs:
            return sorted(fcs), None
    except:
        arcpy.env.workspace = saved_ws

    # Method 2: da.Walk
    try:
        fcs = []
        for d, dn, fn in arcpy.da.Walk(sde_path, datatype="FeatureClass"):
            fcs.extend(fn)
        if fcs:
            return sorted(fcs), None
    except:
        pass

    # Method 3: Describe children
    try:
        fcs = []
        desc = arcpy.Describe(sde_path)
        if hasattr(desc, 'children'):
            for child in desc.children:
                if getattr(child, 'dataType', '') == "FeatureClass":
                    fcs.append(child.name)
        if fcs:
            return sorted(fcs), None
    except:
        pass

    # Method 4: Split connection + dataset
    try:
        conn = os.path.dirname(sde_path)
        ds = os.path.basename(sde_path)
        arcpy.env.workspace = conn
        fcs = arcpy.ListFeatureClasses(feature_dataset=ds) or []
        arcpy.env.workspace = saved_ws
        if fcs:
            return sorted(fcs), None
    except:
        arcpy.env.workspace = saved_ws

    return [], "All 4 methods failed. Check SDE connection and path."


def get_file_info(folder, filename):
    """Return (size_MB, modified_date_str) for a file"""
    fp = os.path.join(folder, filename)
    try:
        sz = os.path.getsize(fp) / (1024 * 1024)
        mt = datetime.fromtimestamp(os.path.getmtime(fp)).strftime("%Y-%m-%d %H:%M")
        return sz, mt
    except:
        return 0, "unknown"


def _try_add_to_map(fc_path):
    """Attempt to add feature class to the active ArcGIS Pro map"""
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap
        if m:
            m.addDataFromPath(fc_path)
            log("  Added to active map ✓", "OK")
        else:
            log("  No active map found — open a map first", "WARN")
    except Exception as ex:
        log(f"  Could not add to map: {ex}", "WARN")


def _cleanup_safe(*layer_names):
    """Safely delete temp layers/FCs"""
    for nm in layer_names:
        try:
            if nm and arcpy.Exists(nm):
                arcpy.Delete_management(nm)
        except:
            pass


# ── Initial loads ──
sde_target_fcs, sde_error = load_sde_targets(DEFAULT_SDE_WS)
initial_dwg_files = scan_dwg_folder(DEFAULT_DWG_FOLDER)


# ============================================================
# BUILD UI WIDGETS
# ============================================================
style_w = {'description_width': '150px'}
layout_w = widgets.Layout(width='700px')
layout_btn = widgets.Layout(width='180px')

# ── Source Configuration ──
w_project = widgets.Text(
    description="Project #:",
    placeholder="e.g., 86-12-12 or 86121200",
    style={'description_width': '100px'},
    layout=widgets.Layout(width='350px')
)
btn_create_gdb = widgets.Button(
    description="📦 Create Temp GDB",
    button_style='',
    layout=widgets.Layout(width='180px')
)
w_temp_status = widgets.HTML(
    value="<i style='color:#888'>Enter project # → click Create</i>"
)
w_dwg_folder = widgets.Text(
    value=DEFAULT_DWG_FOLDER,
    description="DWG Folder:",
    style={'description_width': '100px'},
    layout=widgets.Layout(width='620px')
)
btn_scan = widgets.Button(
    description="📂 Scan Folder",
    button_style='info',
    layout=widgets.Layout(width='140px')
)

# ── DWG Selection ──
w_dwg = widgets.Dropdown(
    options=[PH] + initial_dwg_files, value=PH,
    description="1️⃣ DWG File:", style=style_w, layout=layout_w
)
w_type = widgets.Dropdown(
    options=[PH], value=PH,
    description="2️⃣ Feature Type:", style=style_w, layout=layout_w
)
w_layer = widgets.Dropdown(
    options=[PH], value=PH,
    description="3️⃣ CAD Layer:", style=style_w, layout=layout_w
)

# ── Output Configuration ──
w_sde_path = widgets.Text(
    value=DEFAULT_SDE_WS,
    description="SDE Path:",
    style={'description_width': '100px'},
    layout=widgets.Layout(width='600px')
)
btn_reload_sde = widgets.Button(
    description="🔄 Reload SDE",
    button_style='',
    layout=widgets.Layout(width='140px')
)

target_opts = [PH] + sde_target_fcs if sde_target_fcs else [PH + " (SDE not loaded)"]
w_target = widgets.Dropdown(
    options=target_opts, value=target_opts[0],
    description="4️⃣ Target Schema:", style=style_w, layout=layout_w
)
w_gdb = widgets.Text(
    value=DEFAULT_QC_GDB,
    description="5️⃣ Output GDB:",
    placeholder="Full path to output geodatabase",
    style=style_w, layout=layout_w
)
w_name = widgets.Text(
    description="6️⃣ Output FC Name:",
    placeholder="e.g., WATER_MAIN_QAQC",
    style=style_w, layout=layout_w
)

# ── Preview bar ──
w_preview = widgets.HTML(
    value="<i>Select DWG → Feature Type → Layer to see preview</i>"
)

# ── Action Buttons ──
btn_preview = widgets.Button(
    description="👁️ Preview", button_style='info',
    disabled=True, layout=layout_btn
)
btn_run = widgets.Button(
    description="🚀 Digitize (Schema)", button_style='success',
    disabled=True, layout=widgets.Layout(width='195px')
)
btn_export_raw = widgets.Button(
    description="📦 Export Raw Layer", button_style='primary',
    disabled=True, layout=widgets.Layout(width='195px')
)
# ────────────────────────────────────────────────────────────
# NEW BUTTON: Export Full DWG as Polyline
# ────────────────────────────────────────────────────────────
btn_full_dwg = widgets.Button(
    description="📄 Export Full DWG",
    button_style='',
    disabled=True,
    tooltip="Export ALL polylines from entire DWG file with original DWG attributes",
    layout=widgets.Layout(width='195px')
)

btn_clear = widgets.Button(
    description="🧹 Clear Log", button_style='warning',
    layout=widgets.Layout(width='140px')
)
btn_history = widgets.Button(
    description="📊 Session History", button_style='',
    layout=layout_btn
)
btn_save_log = widgets.Button(
    description="💾 Save Log", button_style='',
    layout=widgets.Layout(width='140px')
)

# ── Options ──
chk_append = widgets.Checkbox(
    value=False, description="Append to existing FC (don't overwrite)", indent=False
)
chk_add_map = widgets.Checkbox(
    value=False, description="Add result to active ArcGIS Pro map", indent=False
)

# ── Log output ──
w_log = widgets.Output(layout={
    'border': '1px solid #999', 'height': '450px', 'overflow_y': 'auto'
})


# ============================================================
# ASSEMBLE UI LAYOUT
# ============================================================
ui = widgets.VBox([
    widgets.HTML(
        "<h2>🛠️ DWG → GDB Digitization Tool v2.1</h2>"
        "<p style='color:#555;margin:0'>Direct DWG read • Schema mapping • "
        "Raw export • Full DWG export • Session tracking</p><hr>"
    ),

    # Source Configuration
    widgets.HTML("<b style='font-size:14px'>📂 Source Configuration</b>"),
    widgets.HBox([w_project, btn_create_gdb, w_temp_status]),
    widgets.HBox([w_dwg_folder, btn_scan]),
    widgets.HTML("<hr>"),

    # DWG Selection
    widgets.HTML("<b style='font-size:14px'>🗂️ DWG Selection</b>"),
    w_dwg, w_type, w_layer,
    widgets.HTML("<hr>"),

    # Output Configuration
    widgets.HTML("<b style='font-size:14px'>📤 Output Configuration</b>"),
    widgets.HBox([w_sde_path, btn_reload_sde]),
    w_target, w_gdb, w_name,
    w_preview,
    widgets.HTML("<hr>"),

    # Actions — 4 buttons on first row
    widgets.HTML("<b style='font-size:14px'>⚡ Actions</b>"),
    widgets.HTML(
        "<p style='color:#555;margin:2px 0;font-size:12px'>"
        "🚀 Schema = SDE template &nbsp;|&nbsp; "
        "📦 Raw Layer = selected layer with DWG attributes &nbsp;|&nbsp; "
        "📄 Full DWG = ALL polylines from entire DWG file</p>"
    ),
    widgets.HBox([btn_preview, btn_run, btn_export_raw, btn_full_dwg]),
    widgets.HBox([btn_clear, btn_history, btn_save_log]),
    widgets.HBox([chk_append, chk_add_map]),
    widgets.HTML("<hr><b>📋 Processing Log:</b>"),
    w_log
])

display(ui)


# ============================================================
# BUTTON STATE MANAGEMENT
# ============================================================
def refresh_buttons(*_):
    """Enable/disable buttons based on current widget values"""
    has_dwg = is_real(w_dwg)
    has_type = has_dwg and is_real(w_type)
    has_layer = has_type and (is_real(w_layer) or is_all_layers())
    has_output = bool(w_gdb.value.strip()) and bool(w_name.value.strip())
    has_schema = has_layer and is_real(w_target) and has_output

    btn_preview.disabled = not has_layer
    btn_run.disabled = not has_schema
    btn_export_raw.disabled = not (has_layer and has_output)

    # Full DWG export only needs: DWG selected + output GDB exists
    # Does NOT need layer, type, target schema, or FC name
    btn_full_dwg.disabled = not (has_dwg and bool(w_gdb.value.strip()))


for _w in [w_dwg, w_type, w_layer, w_target, w_name, w_gdb]:
    _w.observe(refresh_buttons, names='value')


# ============================================================
# 📂 SCAN FOLDER BUTTON
# ============================================================
def on_scan_folder(_):
    """Rescan DWG folder and refresh file dropdown"""
    global CURRENT_DWG
    folder = w_dwg_folder.value.strip()

    with w_log:
        log(f"Scanning folder: {folder}")

    if not os.path.exists(folder):
        with w_log:
            log(f"Folder not found: {folder}", "ERR")
        w_dwg.options = [PH + " — folder not found"]
        return

    files = scan_dwg_folder(folder)

    CURRENT_DWG = None
    w_dwg.options = [PH] + files
    w_dwg.value = PH
    w_type.options = [PH]; w_type.value = PH
    w_layer.options = [PH]; w_layer.value = PH

    with w_log:
        if files:
            log(f"Found {len(files)} DWG file(s):", "OK")
            total_mb = 0
            for f in files:
                sz, mt = get_file_info(folder, f)
                total_mb += sz
                log(f"  📄 {f:<40} {sz:>6.1f} MB   ({mt})")
            log(f"  Total: {len(files)} files, {total_mb:.1f} MB")
        else:
            log("No .dwg files found in this folder", "WARN")

    refresh_buttons()

btn_scan.on_click(on_scan_folder)


# ============================================================
# 📦 CREATE TEMP GDB  (FIXED naming convention)
# ============================================================
def on_create_gdb(_):
    """
    Auto-create Project_<ProjectNo>_temp.gdb in DWG folder.
    
    Naming examples:
        Project # = 86-12-12   →  Project_86-12-12_temp.gdb
        Project # = 86121200   →  Project_86121200_temp.gdb
        Project # = MDC-2025-001 → Project_MDC-2025-001_temp.gdb
    """
    proj = w_project.value.strip()
    folder = w_dwg_folder.value.strip()

    if not proj:
        w_temp_status.value = (
            "<span style='color:orange'>⚠️ Enter a project number first</span>"
        )
        with w_log:
            log("Enter a project number to create temp GDB", "WARN")
        return

    if not os.path.exists(folder):
        w_temp_status.value = (
            "<span style='color:red'>❌ DWG folder not found</span>"
        )
        with w_log:
            log(f"Folder not found: {folder}", "ERR")
        return

    # ── Build GDB name preserving project number format ──
    gdb_name = make_gdb_name(proj)
    gdb_path = os.path.join(folder, gdb_name)

    with w_log:
        log(f"Project #: {proj}")
        log(f"GDB Name : {gdb_name}")
        log(f"Full Path: {gdb_path}")

        if arcpy.Exists(gdb_path):
            log(f"Temp GDB already exists — reusing: {gdb_name}", "OK")
        else:
            log(f"Creating: {gdb_name} ...")
            try:
                arcpy.management.CreateFileGDB(folder, gdb_name)
                log(f"Created successfully: {gdb_path}", "OK")
            except Exception as ex:
                log(f"Failed to create GDB: {ex}", "ERR")
                w_temp_status.value = (
                    f"<span style='color:red'>❌ {ex}</span>"
                )
                return

    # Auto-fill output GDB widget
    w_gdb.value = gdb_path
    w_temp_status.value = (
        f"<span style='color:green'>✅ <b>{gdb_name}</b> → set as Output GDB</span>"
    )
    with w_log:
        log(f"Output GDB auto-set to: {gdb_path}", "OK")

    refresh_buttons()

btn_create_gdb.on_click(on_create_gdb)


# ============================================================
# DWG FILE SELECTED → scan geometry types
# ============================================================
def on_dwg_changed(change):
    global CURRENT_DWG

    w_type.options = [PH]; w_type.value = PH
    w_layer.options = [PH]; w_layer.value = PH
    w_preview.value = "<i>Select Feature Type next</i>"

    val = change['new']
    if val == PH:
        CURRENT_DWG = None
        refresh_buttons()
        return

    folder = w_dwg_folder.value.strip()
    CURRENT_DWG = os.path.join(folder, val)

    with w_log:
        log(f"Selected DWG: {val}")
        if not os.path.exists(CURRENT_DWG):
            log(f"File not found: {CURRENT_DWG}", "ERR")
            CURRENT_DWG = None
            refresh_buttons()
            return

        sz, mt = get_file_info(folder, val)
        log(f"  Size: {sz:.2f} MB | Modified: {mt}", "DETAIL")
        log("Scanning geometry types...")

    types_found = []
    for geom in ['Polyline', 'Point', 'Polygon', 'Annotation', 'MultiPatch']:
        fc = os.path.join(CURRENT_DWG, geom)
        try:
            if arcpy.Exists(fc):
                n = int(arcpy.GetCount_management(fc)[0])
                if n > 0:
                    types_found.append(f"{geom} ({n} features)")
                    with w_log:
                        log(f"  ✓ {geom}: {n:,} features")
        except Exception as ex:
            with w_log:
                log(f"  ✗ {geom}: {ex}", "WARN")

    if types_found:
        w_type.options = [PH] + types_found
        with w_log:
            log(f"Found {len(types_found)} geometry type(s)", "OK")
    else:
        w_type.options = [PH + " — no geometry found"]
        with w_log:
            log("No geometry found in DWG", "WARN")

    refresh_buttons()

w_dwg.observe(on_dwg_changed, names='value')


# ============================================================
# FEATURE TYPE SELECTED → list CAD layers
# ============================================================
def on_type_changed(change):
    global CURRENT_DWG

    w_layer.options = [PH]; w_layer.value = PH
    w_preview.value = "<i>Select CAD Layer next</i>"

    val = change['new']
    if not val or val == PH or str(val).startswith("── Select") or not CURRENT_DWG:
        refresh_buttons()
        return

    geom = val.split(" (")[0]
    fc_path = os.path.join(CURRENT_DWG, geom)

    with w_log:
        log(f"Reading layers from {geom}...")

    try:
        if not arcpy.Exists(fc_path):
            with w_log:
                log(f"Not accessible: {fc_path}", "ERR")
            refresh_buttons()
            return

        fld_names = [f.name for f in arcpy.ListFields(fc_path)]
        if 'Layer' not in fld_names:
            with w_log:
                log(f"No 'Layer' field. Fields: {', '.join(fld_names)}", "ERR")
            refresh_buttons()
            return

        # Collect unique layer names with counts
        layer_counts = {}
        with arcpy.da.SearchCursor(fc_path, ["Layer"]) as cur:
            for row in cur:
                lname = str(row[0]).strip() if row[0] else ""
                if lname:
                    layer_counts[lname] = layer_counts.get(lname, 0) + 1

        layers_sorted = sorted(layer_counts.keys())

        if layers_sorted:
            w_layer.options = [PH, ALL_LYR] + layers_sorted
            w_layer.value = PH
            with w_log:
                total = sum(layer_counts.values())
                log(f"Found {len(layers_sorted)} CAD layers ({total:,} total features):", "OK")
                for ly in layers_sorted[:40]:
                    log(f"  • {ly}  ({layer_counts[ly]:,})")
                if len(layers_sorted) > 40:
                    log(f"  ... and {len(layers_sorted) - 40} more")
        else:
            w_layer.options = [PH + " — no layers found"]
            with w_log:
                log("No Layer values found", "WARN")

    except Exception as ex:
        w_layer.options = [PH + " — error"]
        with w_log:
            log(f"Error reading layers: {ex}", "ERR")
            import traceback; traceback.print_exc()

    refresh_buttons()

w_type.observe(on_type_changed, names='value')


# ============================================================
# LAYER SELECTED → Detailed Preview
# ============================================================
def on_layer_changed(change):
    refresh_buttons()
    val = change['new']
    if val and val != PH and not str(val).startswith("── Select"):
        do_detailed_preview()

w_layer.observe(on_layer_changed, names='value')


def do_detailed_preview(_btn=None):
    """Rich preview: count, geometry, SR, extent, fields, sample data"""
    global CURRENT_DWG

    if not CURRENT_DWG or not is_real(w_type):
        w_preview.value = "<span style='color:orange'>⚠️ Select DWG and Feature Type first</span>"
        return
    if not (is_real(w_layer) or is_all_layers()):
        w_preview.value = "<span style='color:orange'>⚠️ Select a CAD Layer</span>"
        return

    geom = w_type.value.split(" (")[0]
    fc_path = os.path.join(CURRENT_DWG, geom)
    layer_name = w_layer.value
    use_all = is_all_layers()
    lyr = "___detail_preview_lyr"

    try:
        if arcpy.Exists(lyr):
            arcpy.Delete_management(lyr)

        if use_all:
            where = None
            display_label = f"ALL LAYERS ({geom})"
        else:
            safe = layer_name.replace("'", "''")
            where = f"Layer = '{safe}'"
            display_label = layer_name

        arcpy.MakeFeatureLayer_management(fc_path, lyr, where)
        count = int(arcpy.GetCount_management(lyr)[0])

        with w_log:
            log("─" * 55)
            log(f"📋 DETAILED PREVIEW: '{display_label}'", "DETAIL")
            log("─" * 55)
            log(f"  Feature Count : {count:,}")

            if count > 0:
                desc = arcpy.Describe(lyr)
                sr = desc.spatialReference
                ext = desc.extent

                log(f"  Geometry Type : {desc.shapeType}")
                log(f"  Spatial Ref   : {sr.name}")
                log(f"  EPSG Code     : {sr.factoryCode}")
                if sr.type == 'Projected':
                    log(f"  Linear Unit   : {sr.linearUnitName}")
                    try:
                        log(f"  GCS           : {sr.GCS.name}")
                    except:
                        pass

                log(f"  Extent:")
                log(f"    X: {ext.XMin:>14.4f}  →  {ext.XMax:>14.4f}")
                log(f"    Y: {ext.YMin:>14.4f}  →  {ext.YMax:>14.4f}")
                width = ext.XMax - ext.XMin
                height = ext.YMax - ext.YMin
                log(f"    Width: {width:.2f}  Height: {height:.2f}")

                # Fields
                fields = arcpy.ListFields(lyr)
                skip = {'Shape', 'Shape_Length', 'Shape_Area', 'OBJECTID', 'FID'}
                user_fields = [f for f in fields
                               if f.name not in skip and f.type != 'Geometry']

                log(f"  Fields ({len(user_fields)}):")
                for f in user_fields:
                    nullable = "nullable" if f.isNullable else "required"
                    log(f"    • {f.name:<25} {f.type:<12} len={f.length}  ({nullable})")

                # Sample data
                sample_names = [f.name for f in user_fields][:10]
                if sample_names:
                    log(f"  Sample Data (first 5):")
                    log(f"    {'  |  '.join(n[:15] for n in sample_names)}")
                    log(f"    {'─' * min(80, len(sample_names) * 17)}")
                    row_num = 0
                    with arcpy.da.SearchCursor(lyr, sample_names) as cur:
                        for row in cur:
                            if row_num >= 5:
                                break
                            vals = [str(v)[:15] if v is not None else "NULL"
                                    for v in row]
                            log(f"    {'  |  '.join(vals)}")
                            row_num += 1

                # Layer breakdown when ALL LAYERS
                if use_all:
                    log(f"  Layer Breakdown:")
                    lyr_counts = {}
                    with arcpy.da.SearchCursor(lyr, ["Layer"]) as cur:
                        for row in cur:
                            ln = str(row[0]).strip() if row[0] else "(empty)"
                            lyr_counts[ln] = lyr_counts.get(ln, 0) + 1
                    for ln in sorted(lyr_counts.keys()):
                        log(f"    • {ln}: {lyr_counts[ln]:,}")

            log("─" * 55)

        # Update preview bar
        if count > 0:
            desc = arcpy.Describe(lyr)
            sr = desc.spatialReference
            w_preview.value = f"""
            <div style='background:#e8f5e9; padding:10px; border-radius:5px;
                        border:1px solid #66bb6a; margin:5px 0;'>
                <b>✅ {count:,} feature(s)</b> &nbsp;|&nbsp;
                <b>Layer:</b> {display_label} &nbsp;|&nbsp;
                <b>Geometry:</b> {desc.shapeType} &nbsp;|&nbsp;
                <b>SR:</b> {sr.name} (EPSG:{sr.factoryCode})
            </div>"""
        else:
            w_preview.value = (
                f"<span style='color:orange'>⚠️ 0 features for "
                f"'{display_label}'</span>"
            )

        if arcpy.Exists(lyr):
            arcpy.Delete_management(lyr)

    except Exception as ex:
        w_preview.value = f"<span style='color:red'>❌ Preview error: {ex}</span>"
        with w_log:
            log(f"Preview error: {ex}", "ERR")

btn_preview.on_click(do_detailed_preview)


# ============================================================
# 🚀 DIGITIZE WITH SCHEMA
# ============================================================
def on_digitize(_):
    """Filter CAD layer → create FC with SDE schema → project → append"""
    global CURRENT_DWG

    with w_log:
        log("═" * 55)
        log("🚀 STARTING DIGITIZATION (WITH SCHEMA)", "OK")
        log("═" * 55)

        if not CURRENT_DWG:
            log("No DWG loaded", "ERR"); return
        if not is_real(w_type):
            log("Select a Feature Type", "ERR"); return
        if not (is_real(w_layer) or is_all_layers()):
            log("Select a CAD Layer", "ERR"); return
        if not is_real(w_target):
            log("Select a Target Schema", "ERR"); return

        out_fc_name = w_name.value.strip()
        out_gdb = w_gdb.value.strip()
        sde_path = w_sde_path.value.strip()
        if not out_fc_name:
            log("Enter Output FC Name", "ERR"); return
        if not out_gdb:
            log("Enter Output GDB path", "ERR"); return

        geom = w_type.value.split(" (")[0]
        layer_name = w_layer.value
        target_name = w_target.value
        use_all = is_all_layers()

        cad_fc = os.path.join(CURRENT_DWG, geom)
        target_fc = os.path.join(sde_path, target_name)
        out_fc = os.path.join(out_gdb, out_fc_name)

        log(f"DWG:    {os.path.basename(CURRENT_DWG)}")
        log(f"Type:   {geom}")
        log(f"Layer:  {'ALL LAYERS' if use_all else layer_name}")
        log(f"Schema: {target_name}")
        log(f"Output: {out_gdb}\\{out_fc_name}")

        if not arcpy.Exists(cad_fc):
            log(f"CAD FC not found: {cad_fc}", "ERR"); return
        if not arcpy.Exists(target_fc):
            log(f"Target schema not found: {target_fc}", "ERR")
            log("Check SDE connection", "WARN"); return
        if not arcpy.Exists(out_gdb):
            log(f"Output GDB not found: {out_gdb}", "ERR"); return

        lyr = "___digi_schema_lyr"
        temp_proj = os.path.join(out_gdb, f"__temp_proj_{out_fc_name}")

        try:
            # STEP 1: Filter
            if arcpy.Exists(lyr):
                arcpy.Delete_management(lyr)

            if use_all:
                where = None
                log("Step 1: Selecting ALL features (no layer filter)")
            else:
                safe = layer_name.replace("'", "''")
                where = f"Layer = '{safe}'"
                log(f"Step 1: Filtering → {where}")

            arcpy.MakeFeatureLayer_management(cad_fc, lyr, where)
            count = int(arcpy.GetCount_management(lyr)[0])
            if count == 0:
                log("No features matched filter", "WARN")
                arcpy.Delete_management(lyr); return
            log(f"  → {count:,} features selected", "OK")

            # STEP 2: Geometry & SR check
            src_desc = arcpy.Describe(lyr)
            tgt_desc = arcpy.Describe(target_fc)
            src_geom = src_desc.shapeType
            tgt_geom = tgt_desc.shapeType
            src_sr = src_desc.spatialReference
            tgt_sr = tgt_desc.spatialReference

            log(f"Step 2: Source={src_geom} ({src_sr.name}) → "
                f"Target={tgt_geom} ({tgt_sr.name})")

            if src_geom.lower() != tgt_geom.lower():
                log(f"Geometry MISMATCH: {src_geom} ≠ {tgt_geom}", "ERR")
                arcpy.Delete_management(lyr); return
            log("  → Geometry match ✓", "OK")

            # Field mapping preview
            src_fields = {f.name.upper() for f in arcpy.ListFields(lyr)
                         if f.name not in ('Shape', 'OBJECTID', 'FID',
                                           'Shape_Length', 'Shape_Area')
                         and f.type != 'Geometry'}
            tgt_fields = {f.name.upper() for f in arcpy.ListFields(target_fc)
                         if f.name not in ('Shape', 'OBJECTID', 'FID',
                                           'Shape_Length', 'Shape_Area', 'GLOBALID')
                         and f.type not in ('Geometry', 'GlobalID')}
            matched = src_fields & tgt_fields
            log(f"  Field mapping: {len(matched)} match, "
                f"{len(src_fields - tgt_fields)} source-only, "
                f"{len(tgt_fields - src_fields)} target-only")

            # STEP 3: Create/prepare output
            if arcpy.Exists(out_fc):
                if chk_append.value:
                    log("Step 3: Output exists → APPEND mode", "WARN")
                else:
                    arcpy.Delete_management(out_fc)
                    log("Step 3: Output exists → deleted for recreation")

            if not arcpy.Exists(out_fc):
                arcpy.management.CreateFeatureclass(
                    out_gdb, out_fc_name,
                    geometry_type=tgt_geom.upper(),
                    template=target_fc,
                    spatial_reference=tgt_sr
                )
                log(f"  → Created {out_fc_name} (schema from {target_name})", "OK")

            # STEP 4: Project if needed
            input_data = lyr
            needs_proj = (src_sr.factoryCode != tgt_sr.factoryCode
                         and src_sr.factoryCode != 0)
            if needs_proj:
                log(f"Step 4: Projecting {src_sr.name} → {tgt_sr.name}...")
                if arcpy.Exists(temp_proj):
                    arcpy.Delete_management(temp_proj)
                arcpy.management.Project(lyr, temp_proj, tgt_sr)
                input_data = temp_proj
                log("  → Projection complete", "OK")
            else:
                log("Step 4: No projection needed")

            # STEP 5: Append
            log(f"Step 5: Appending {count:,} features...")
            arcpy.management.Append(input_data, out_fc, "NO_TEST")

            final_count = int(arcpy.GetCount_management(out_fc)[0])
            _cleanup_safe(lyr, temp_proj)

            if chk_add_map.value:
                _try_add_to_map(out_fc)

            SESSION_HISTORY.append({
                'time': datetime.now().strftime("%H:%M:%S"),
                'dwg': os.path.basename(CURRENT_DWG),
                'layer': 'ALL' if use_all else layer_name,
                'mode': 'Schema',
                'schema': target_name,
                'output': out_fc_name,
                'count': final_count,
                'gdb': os.path.basename(out_gdb)
            })

            log("═" * 55)
            log(f"✅ DIGITIZATION COMPLETE!", "OK")
            log(f"   Output   : {out_fc}", "OK")
            log(f"   Features : {final_count:,}", "OK")
            log(f"   Schema   : {target_name}", "OK")
            log("═" * 55)

        except Exception as ex:
            log(f"DIGITIZATION FAILED: {ex}", "ERR")
            import traceback; traceback.print_exc()
            _cleanup_safe(lyr, temp_proj)

btn_run.on_click(on_digitize)


# ============================================================
# 📦 EXPORT RAW LAYER — selected layer with DWG attributes
# ============================================================
def on_export_raw(_):
    """Export selected CAD layer with all original DWG attributes"""
    global CURRENT_DWG

    with w_log:
        log("═" * 55)
        log("📦 EXPORT RAW LAYER (ORIGINAL DWG ATTRIBUTES)", "OK")
        log("═" * 55)

        if not CURRENT_DWG:
            log("No DWG loaded", "ERR"); return
        if not is_real(w_type):
            log("Select Feature Type", "ERR"); return
        if not (is_real(w_layer) or is_all_layers()):
            log("Select CAD Layer", "ERR"); return

        out_fc_name = w_name.value.strip()
        out_gdb = w_gdb.value.strip()
        if not out_fc_name:
            log("Enter Output FC Name", "ERR"); return
        if not out_gdb:
            log("Enter Output GDB path", "ERR"); return
        if not arcpy.Exists(out_gdb):
            log(f"Output GDB not found: {out_gdb}", "ERR"); return

        geom = w_type.value.split(" (")[0]
        cad_fc = os.path.join(CURRENT_DWG, geom)
        layer_name = w_layer.value
        use_all = is_all_layers()
        out_fc = os.path.join(out_gdb, out_fc_name)

        if not arcpy.Exists(cad_fc):
            log(f"CAD FC not found: {cad_fc}", "ERR"); return

        lyr = "___raw_export_lyr"

        try:
            if arcpy.Exists(lyr):
                arcpy.Delete_management(lyr)

            if use_all:
                where = None
                log(f"Exporting ALL {geom} features (no layer filter)")
            else:
                safe = layer_name.replace("'", "''")
                where = f"Layer = '{safe}'"
                log(f"Exporting layer: {layer_name}")

            arcpy.MakeFeatureLayer_management(cad_fc, lyr, where)
            count = int(arcpy.GetCount_management(lyr)[0])
            if count == 0:
                log("No features to export", "WARN")
                arcpy.Delete_management(lyr); return
            log(f"  → {count:,} features to export", "OK")

            if arcpy.Exists(out_fc):
                if chk_append.value:
                    log("Appending to existing FC", "WARN")
                    arcpy.management.Append(lyr, out_fc, "NO_TEST")
                else:
                    log("Overwriting existing FC")
                    arcpy.Delete_management(out_fc)
                    arcpy.conversion.FeatureClassToFeatureClass(
                        lyr, out_gdb, out_fc_name
                    )
            else:
                arcpy.conversion.FeatureClassToFeatureClass(
                    lyr, out_gdb, out_fc_name
                )

            final_count = int(arcpy.GetCount_management(out_fc)[0])

            out_fields = arcpy.ListFields(out_fc)
            skip = {'OBJECTID', 'FID', 'Shape', 'Shape_Length', 'Shape_Area'}
            user_flds = [f for f in out_fields
                        if f.name not in skip and f.type != 'Geometry']
            log(f"  Exported fields ({len(user_flds)}):", "DETAIL")
            for f in user_flds:
                log(f"    • {f.name:<25} ({f.type})")

            if arcpy.Exists(lyr):
                arcpy.Delete_management(lyr)
            if chk_add_map.value:
                _try_add_to_map(out_fc)

            SESSION_HISTORY.append({
                'time': datetime.now().strftime("%H:%M:%S"),
                'dwg': os.path.basename(CURRENT_DWG),
                'layer': 'ALL' if use_all else layer_name,
                'mode': 'Raw Layer',
                'schema': 'N/A (DWG attributes)',
                'output': out_fc_name,
                'count': final_count,
                'gdb': os.path.basename(out_gdb)
            })

            log("═" * 55)
            log(f"✅ RAW LAYER EXPORT COMPLETE!", "OK")
            log(f"   Output   : {out_fc}", "OK")
            log(f"   Features : {final_count:,}", "OK")
            log("═" * 55)

        except Exception as ex:
            log(f"RAW EXPORT FAILED: {ex}", "ERR")
            import traceback; traceback.print_exc()
            _cleanup_safe(lyr)

btn_export_raw.on_click(on_export_raw)


# ============================================================
# 📄 EXPORT FULL DWG AS POLYLINE  (NEW — Request #3 clarified)
# ============================================================
def on_full_dwg_export(_):
    """
    Export the ENTIRE DWG file as a single Polyline feature class.
    
    - No layer filter: ALL polylines from the whole DWG
    - No schema template: preserves original DWG attributes
      (Layer, Color, Linetype, Elevation, LineWt, etc.)
    - No need to select Feature Type, CAD Layer, or Target Schema
    - Auto-names the output FC from the DWG filename
    - Outputs to the current Output GDB
    
    This is the "one-click full DWG digitization" option.
    """
    global CURRENT_DWG

    with w_log:
        log("═" * 55)
        log("📄 EXPORT FULL DWG → POLYLINE (ALL LAYERS, DWG ATTRIBUTES)", "OK")
        log("═" * 55)

        # ── Validate ──
        if not CURRENT_DWG:
            log("No DWG file selected", "ERR"); return

        if not os.path.exists(CURRENT_DWG):
            log(f"DWG file not found: {CURRENT_DWG}", "ERR"); return

        out_gdb = w_gdb.value.strip()
        if not out_gdb:
            log("Enter an Output GDB path (or create temp GDB first)", "ERR")
            return
        if not arcpy.Exists(out_gdb):
            log(f"Output GDB not found: {out_gdb}", "ERR")
            log("Create it via '📦 Create Temp GDB' button", "WARN")
            return

        # ── Build paths ──
        dwg_basename = os.path.splitext(os.path.basename(CURRENT_DWG))[0]
        polyline_fc = os.path.join(CURRENT_DWG, "Polyline")

        # Auto-generate FC name from DWG filename
        auto_fc_name = make_fc_name(dwg_basename) + "_Polyline"
        out_fc = os.path.join(out_gdb, auto_fc_name)

        log(f"DWG File    : {os.path.basename(CURRENT_DWG)}")
        sz, mt = get_file_info(
            os.path.dirname(CURRENT_DWG),
            os.path.basename(CURRENT_DWG)
        )
        log(f"File Size   : {sz:.2f} MB")
        log(f"Modified    : {mt}")
        log(f"Output GDB  : {os.path.basename(out_gdb)}")
        log(f"Output FC   : {auto_fc_name}")
        log("")

        # ── Check Polyline exists in DWG ──
        if not arcpy.Exists(polyline_fc):
            log("No Polyline geometry found in this DWG file", "ERR")
            log("The DWG may only contain points, polygons, or annotations", "WARN")

            # Show what IS available
            log("Available geometry types in this DWG:")
            for geom in ['Polyline', 'Point', 'Polygon', 'Annotation', 'MultiPatch']:
                gfc = os.path.join(CURRENT_DWG, geom)
                try:
                    if arcpy.Exists(gfc):
                        n = int(arcpy.GetCount_management(gfc)[0])
                        log(f"  ✓ {geom}: {n:,} features")
                    else:
                        log(f"  ✗ {geom}: not present")
                except:
                    log(f"  ✗ {geom}: error reading")
            return

        # ── Count total polyline features ──
        total_count = int(arcpy.GetCount_management(polyline_fc)[0])
        log(f"Total Polyline features in DWG: {total_count:,}", "OK")

        if total_count == 0:
            log("DWG contains Polyline type but has 0 features", "WARN")
            return

        # ── Show layer breakdown before export ──
        log("Layer breakdown:")
        try:
            layer_counts = {}
            with arcpy.da.SearchCursor(polyline_fc, ["Layer"]) as cur:
                for row in cur:
                    ln = str(row[0]).strip() if row[0] else "(empty)"
                    layer_counts[ln] = layer_counts.get(ln, 0) + 1
            for ln in sorted(layer_counts.keys()):
                log(f"  • {ln:<40} {layer_counts[ln]:>6,} features")
            log(f"  {'─' * 50}")
            log(f"  {'TOTAL':<40} {total_count:>6,} features")
        except Exception as ex:
            log(f"  Could not read layer breakdown: {ex}", "WARN")
        log("")

        # ── Show spatial reference info ──
        try:
            desc = arcpy.Describe(polyline_fc)
            sr = desc.spatialReference
            ext = desc.extent
            log(f"Spatial Reference: {sr.name} (EPSG:{sr.factoryCode})")
            log(f"Extent: X({ext.XMin:.2f} → {ext.XMax:.2f}), "
                f"Y({ext.YMin:.2f} → {ext.YMax:.2f})")
        except:
            pass
        log("")

        # ── Show DWG attribute fields ──
        try:
            fields = arcpy.ListFields(polyline_fc)
            skip = {'OBJECTID', 'FID', 'Shape', 'Shape_Length', 'Shape_Area'}
            user_flds = [f for f in fields
                        if f.name not in skip and f.type != 'Geometry']
            log(f"DWG attributes to preserve ({len(user_flds)} fields):")
            for f in user_flds:
                log(f"  • {f.name:<25} {f.type:<12} len={f.length}")
        except:
            pass
        log("")

        # ── Handle existing output ──
        if arcpy.Exists(out_fc):
            if chk_append.value:
                log(f"Output FC exists → APPEND mode", "WARN")
            else:
                log(f"Output FC exists → deleting: {auto_fc_name}")
                arcpy.Delete_management(out_fc)

        # ── Export ──
        try:
            log(f"Exporting {total_count:,} polylines...")

            if arcpy.Exists(out_fc) and chk_append.value:
                # Append to existing
                arcpy.management.Append(polyline_fc, out_fc, "NO_TEST")
            else:
                # Fresh export — no filter, all polylines, all attributes
                arcpy.conversion.FeatureClassToFeatureClass(
                    in_features=polyline_fc,
                    out_path=out_gdb,
                    out_name=auto_fc_name
                )

            final_count = int(arcpy.GetCount_management(out_fc)[0])
            log(f"Export successful: {final_count:,} features", "OK")

            # Verify exported fields
            out_flds = arcpy.ListFields(out_fc)
            out_user = [f for f in out_flds
                       if f.name not in skip and f.type != 'Geometry']
            log(f"Verified {len(out_user)} attribute fields in output", "OK")

            # Add to map
            if chk_add_map.value:
                _try_add_to_map(out_fc)

            # Update the Output FC Name widget so user sees what was created
            w_name.value = auto_fc_name

            # Record in session history
            SESSION_HISTORY.append({
                'time': datetime.now().strftime("%H:%M:%S"),
                'dwg': os.path.basename(CURRENT_DWG),
                'layer': f'ALL ({len(layer_counts)} layers)',
                'mode': 'Full DWG Export',
                'schema': 'N/A (DWG attributes)',
                'output': auto_fc_name,
                'count': final_count,
                'gdb': os.path.basename(out_gdb)
            })

            log("═" * 55)
            log(f"✅ FULL DWG EXPORT COMPLETE!", "OK")
            log(f"   DWG File : {os.path.basename(CURRENT_DWG)}", "OK")
            log(f"   Output   : {out_fc}", "OK")
            log(f"   Features : {final_count:,} polylines", "OK")
            log(f"   Layers   : {len(layer_counts)} CAD layers included", "OK")
            log(f"   Fields   : {len(out_user)} DWG attributes preserved", "OK")
            log("═" * 55)

        except Exception as ex:
            log(f"FULL DWG EXPORT FAILED: {ex}", "ERR")
            import traceback; traceback.print_exc()

btn_full_dwg.on_click(on_full_dwg_export)


# ============================================================
# 🔄 RELOAD SDE
# ============================================================
def on_reload_sde(_):
    sde_path = w_sde_path.value.strip()
    with w_log:
        log(f"Reloading SDE targets from: {sde_path}")

    fcs, err = load_sde_targets(sde_path)

    if fcs:
        w_target.options = [PH] + fcs
        w_target.value = PH
        with w_log:
            log(f"Loaded {len(fcs)} target feature classes:", "OK")
            for fc in fcs[:20]:
                log(f"  • {fc}")
            if len(fcs) > 20:
                log(f"  ... +{len(fcs) - 20} more")
    else:
        w_target.options = [PH + " (failed)"]
        with w_log:
            log("Failed to load SDE targets", "ERR")
            if err:
                log(f"  {err}", "ERR")
            log("  1. Is the SDE connection file valid?", "WARN")
            log("  2. Can you browse this path in Catalog?", "WARN")
            log(f"  3. Path: {sde_path}", "WARN")

    refresh_buttons()

btn_reload_sde.on_click(on_reload_sde)


# ============================================================
# 📊 SESSION HISTORY
# ============================================================
def on_history(_):
    with w_log:
        log("═" * 55)
        log("📊 SESSION HISTORY", "DATA")
        log("═" * 55)

        if not SESSION_HISTORY:
            log("  No operations recorded yet")
        else:
            for i, h in enumerate(SESSION_HISTORY, 1):
                log(
                    f"  [{i}] {h['time']}  {h['mode']:<17} "
                    f"{h['dwg'][:20]} → {h['layer'][:20]} → "
                    f"{h['output']} ({h['count']:,} feat)"
                )
            log("")
            total_ops = len(SESSION_HISTORY)
            total_feat = sum(h['count'] for h in SESSION_HISTORY)
            modes = {}
            for h in SESSION_HISTORY:
                modes[h['mode']] = modes.get(h['mode'], 0) + 1
            log(f"  Total operations : {total_ops}")
            for mode, cnt in sorted(modes.items()):
                log(f"    {mode}: {cnt}")
            log(f"  Total features   : {total_feat:,}")

        log("═" * 55)

btn_history.on_click(on_history)


# ============================================================
# 💾 SAVE LOG TO FILE
# ============================================================
def on_save_log(_):
    folder = w_dwg_folder.value.strip()
    proj = w_project.value.strip() or "session"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Use same naming convention as GDB
    cleaned_proj = re.sub(r'[\\/:*?"<>|]', '', proj.strip()).strip('. ')
    fname = f"Project_{cleaned_proj}_log_{ts}.txt"

    if not os.path.exists(folder):
        folder = os.path.expanduser("~\\Desktop")

    log_path = os.path.join(folder, fname)

    try:
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(f"DWG Digitization Tool v2.1 — Session Log\n")
            f.write(f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Project: {proj}\n")
            f.write("=" * 60 + "\n\n")
            for line in SESSION_LOG_LINES:
                f.write(line + "\n")

            if SESSION_HISTORY:
                f.write("\n" + "=" * 60 + "\n")
                f.write("SESSION HISTORY\n")
                f.write("=" * 60 + "\n")
                for i, h in enumerate(SESSION_HISTORY, 1):
                    f.write(
                        f"[{i}] {h['time']} | {h['mode']} | "
                        f"{h['dwg']} → {h['layer']} → {h['output']} "
                        f"({h['count']} features)\n"
                    )

        with w_log:
            log(f"Log saved: {log_path}", "OK")

    except Exception as ex:
        with w_log:
            log(f"Failed to save log: {ex}", "ERR")

btn_save_log.on_click(on_save_log)


# ============================================================
# 🧹 CLEAR LOG
# ============================================================
def on_clear(_):
    w_log.clear_output()
    with w_log:
        log("Log cleared — ready for new operations")

btn_clear.on_click(on_clear)


# ============================================================
# STARTUP DIAGNOSTICS
# ============================================================
with w_log:
    log("═" * 55)
    log("🛠️  DWG DIGITIZATION TOOL v2.1")
    log("═" * 55)
    log("")

    # System Info
    log("🖥️  SYSTEM INFORMATION", "DETAIL")
    try:
        info = arcpy.GetInstallInfo()
        log(f"  ArcGIS Product  : {info.get('ProductName', 'N/A')}")
        log(f"  ArcGIS Version  : {info.get('Version', 'N/A')} "
            f"(Build {info.get('BuildNumber', 'N/A')})")
        log(f"  Install Dir     : {info.get('InstallDir', 'N/A')}")
    except:
        log(f"  ArcGIS Version  : Could not determine")

    log(f"  Python Version  : {sys.version.split()[0]}")
    log(f"  Python Path     : {sys.executable}")

    try:
        log(f"  License Level   : {arcpy.ProductInfo()}")
    except:
        pass

    log(f"  User            : {os.environ.get('USERNAME', 'unknown')}")
    log(f"  Computer        : {os.environ.get('COMPUTERNAME', 'unknown')}")
    log(f"  Date/Time       : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        log(f"  Scratch Folder  : {arcpy.env.scratchFolder}")
        log(f"  Scratch GDB     : {arcpy.env.scratchGDB}")
    except:
        pass
    log("")

    # DWG Folder
    log("📁 DWG SOURCE FOLDER", "DETAIL")
    log(f"  Path: {DEFAULT_DWG_FOLDER}")
    if os.path.exists(DEFAULT_DWG_FOLDER):
        log(f"  Status: ✓ Accessible", "OK")
        if initial_dwg_files:
            total_mb = 0
            for f in initial_dwg_files:
                sz, mt = get_file_info(DEFAULT_DWG_FOLDER, f)
                total_mb += sz
                log(f"    📄 {f:<40} {sz:>6.1f} MB   ({mt})")
            log(f"  Total: {len(initial_dwg_files)} files, {total_mb:.1f} MB")
        else:
            log("  No .dwg files found", "WARN")

        # Existing GDBs in folder
        try:
            existing_items = os.listdir(DEFAULT_DWG_FOLDER)
            existing_gdbs = [g for g in existing_items
                           if g.lower().endswith('.gdb')
                           and os.path.isdir(os.path.join(DEFAULT_DWG_FOLDER, g))]
            if existing_gdbs:
                log(f"  Existing GDBs in folder:")
                for g in existing_gdbs:
                    log(f"    📦 {g}")
        except:
            pass
    else:
        log(f"  Status: ✗ NOT FOUND", "ERR")
        log("  → Update path and click '📂 Scan Folder'", "WARN")
    log("")

    # Output GDB
    log("💾 OUTPUT GEODATABASE", "DETAIL")
    log(f"  Path: {DEFAULT_QC_GDB}")
    if arcpy.Exists(DEFAULT_QC_GDB):
        log(f"  Status: ✓ Exists", "OK")
        try:
            saved = arcpy.env.workspace
            arcpy.env.workspace = DEFAULT_QC_GDB
            ex_fcs = arcpy.ListFeatureClasses() or []
            arcpy.env.workspace = saved
            log(f"  Existing feature classes: {len(ex_fcs)}")
            for fc in sorted(ex_fcs)[:10]:
                log(f"    • {fc}")
            if len(ex_fcs) > 10:
                log(f"    ... +{len(ex_fcs) - 10} more")
        except:
            pass
    else:
        log(f"  Status: ✗ Not found", "WARN")
        log("  → Create via '📦 Create Temp GDB' or update path", "WARN")
    log("")

    # SDE Connection
    log("🔗 SDE CONNECTION", "DETAIL")
    log(f"  Path: {DEFAULT_SDE_WS}")
    if sde_target_fcs:
        log(f"  Status: ✓ Connected ({len(sde_target_fcs)} feature classes)", "OK")
        for fc_name in sde_target_fcs[:8]:
            log(f"    • {fc_name}")
        if len(sde_target_fcs) > 8:
            log(f"    ... +{len(sde_target_fcs) - 8} more")
    else:
        log(f"  Status: ✗ Could not load", "WARN")
        if sde_error:
            log(f"  Error: {sde_error}", "ERR")
        log("  → Click '🔄 Reload SDE' to retry", "WARN")
    log("")

    # Disk Space
    log("💿 DISK SPACE", "DETAIL")
    try:
        import shutil
        checked = set()
        for label, path in [
            ("DWG Folder", DEFAULT_DWG_FOLDER),
            ("Output GDB", os.path.dirname(DEFAULT_QC_GDB)),
        ]:
            if os.path.exists(path):
                drive = os.path.splitdrive(path)[0]
                if drive and drive not in checked:
                    checked.add(drive)
                    total, used, free = shutil.disk_usage(path)
                    pct = (used / total) * 100
                    log(f"  {drive}\\ ({label}): "
                        f"{free / (1024**3):.1f} GB free of "
                        f"{total / (1024**3):.1f} GB ({pct:.0f}% used)")
    except Exception as ex:
        log(f"  Could not check: {ex}", "WARN")
    log("")

    # Extensions
    log("🔌 EXTENSIONS", "DETAIL")
    for ext in ['Spatial', '3D', 'Network']:
        try:
            status = arcpy.CheckExtension(ext)
            icon = "✓" if status == "Available" else "✗"
            log(f"  {icon} {ext}: {status}")
        except:
            pass
    log("")

    # Active Map
    log("🗺️  ACTIVE MAP", "DETAIL")
    try:
        aprx = arcpy.mp.ArcGISProject("CURRENT")
        m = aprx.activeMap
        if m:
            log(f"  Map: {m.name}", "OK")
            log(f"  SR : {m.spatialReference.name}")
            log(f"  Layers: {len(m.listLayers())}")
        else:
            log("  No active map open", "WARN")
    except:
        log("  Not running inside ArcGIS Pro", "WARN")
    log("")

    # Quick Start
    log("═" * 55)
    log("👉 QUICK START GUIDE", "OK")
    log("═" * 55)
    log("")
    log("  STEP 1 → Enter Project # → '📦 Create Temp GDB'")
    log("           Creates: Project_<your-number>_temp.gdb")
    log("")
    log("  STEP 2 → Select DWG File → Feature Type → CAD Layer")
    log("           (detailed preview auto-generated in log)")
    log("")
    log("  STEP 3 → Choose your action:")
    log("")
    log("    📄 Export Full DWG")
    log("       Exports ALL polylines from the entire DWG file")
    log("       No layer/schema selection needed — one click!")
    log("       Preserves all original DWG attributes")
    log("")
    log("    📦 Export Raw Layer")
    log("       Exports selected CAD layer with DWG attributes")
    log("       Choose specific layer or ALL LAYERS")
    log("")
    log("    🚀 Digitize (Schema)")
    log("       Maps selected layer to SDE schema template")
    log("       For production-ready data with target fields")
    log("")
    log("  💡 TIP: '📄 Export Full DWG' only needs DWG + Output GDB")
    log("  💡 TIP: Change DWG folder anytime via '📂 Scan Folder'")
    log("═" * 55)


