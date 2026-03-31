import arcpy
import pandas as pd

# Set workspace
arcpy.env.workspace = r"N:\EIAMS\GIS\Project_Map_Docs\IAM_QA_QC_ArcGIS_Pro_Project\Connection Files\GIS_DnD@sde2-(OS_Authenticate).sde"

# Input feature class
in_fc = "Trail Segment"

# List to store features with true curves
true_curve_features = []

# Field name for conservation area - change if different in your schema
conservation_area_field = 'Conservation_Area_Name'

# Iterate through features and filter for those with true curves
with arcpy.da.SearchCursor(in_fc, ['OBJECTID', 'Asset_ID', conservation_area_field, 'SHAPE@']) as cursor:
    for row in cursor:
        object_id, asset_id, cons_area_name, geometry = row
        if geometry and geometry.hasCurves:
            true_curve_features.append({
                'FeatureClass': in_fc,
                'OBJECTID': object_id,
                'Asset_ID': asset_id,
                'Conservation_Area': cons_area_name
            })
            print(f"✅ OBJECTID {object_id} | Asset_ID {asset_id} | Area: {cons_area_name} — has true curves.")

# Export to Excel if any curved features are found
if true_curve_features:
    df = pd.DataFrame(true_curve_features)
    output_excel = fr"N:\Kabirr\Completed Assigned Tasks\True_Curves_Export_SDE\{in_fc.replace(' ', '_')}.xlsx"
    df.to_excel(output_excel, index=False)
    print(f"\n📤 Exported {len(true_curve_features)} curved features to Excel:\n{output_excel}")
else:
    print("❌ No features with true curves found.")


import arcpy
import pandas as pd

# Set workspace
arcpy.env.workspace = r"N:\EIAMS\GIS\Project_Map_Docs\IAM_QA_QC_ArcGIS_Pro_Project\Connection Files\GIS_DnD@sde2-(OS_Authenticate).sde"

# Input feature class
in_fc = "Spray Field"

# List to store OBJECTIDs and Asset_IDs with true curves
true_curve_features = []

# Iterate through features and filter for those with true curves
with arcpy.da.SearchCursor(in_fc, ['OBJECTID', 'Asset_ID', 'SHAPE@']) as cursor:
    for row in cursor:
        object_id, asset_id, geometry = row
        if geometry and geometry.hasCurves:
            true_curve_features.append({
                'OBJECTID': object_id,
                'Asset_ID': asset_id
            })
            print(f"✅ Feature with OBJECTID {object_id} and Asset_ID {asset_id} has true curves.")

# Export to Excel if any curved features are found
if true_curve_features:
    df = pd.DataFrame(true_curve_features)
    output_excel = r"N:\Kabirr\Completed Assigned Tasks\True_Curves_Export_SDE\S Field.xlsx"
    df.to_excel(output_excel, index=False)
    print(f"\n📤 Exported {len(true_curve_features)} features with true curves to Excel at:\n{output_excel}")
else:
    print("❌ No features with true curves found.")


import arcpy
import pandas as pd

# Set the workspace to the feature dataset
arcpy.env.workspace = r"N:\EIAMS\GIS\Project_Map_Docs\IAM_QA_QC_ArcGIS_Pro_Project\GIS_Production@sde2_GIS_VIEWER.sde\PRODUCTION.IT.Infrastructure"

# Output Excel path for geometry types
geometry_list_excel = r"N:\Kabirr\Completed Assigned Tasks\Line_Polygon_Feature_Classes.xlsx"

# List all feature classes in the workspace
feature_classes = arcpy.ListFeatureClasses()

# Collect Polyline and Polygon feature classes
geometry_data = []

for fc in feature_classes:
    desc = arcpy.Describe(fc)
    shape_type = desc.shapeType
    if shape_type.lower() in ['polygon', 'polyline']:
        geometry_data.append({
            'FeatureClass': fc,
            'GeometryType': shape_type
        })

# Export the list to Excel
if geometry_data:
    df = pd.DataFrame(geometry_data)
    df.to_excel(geometry_list_excel, index=False)
    print(f"✅ Exported {len(df)} Polyline and Polygon feature classes to:\n{geometry_list_excel}")
else:
    print("❌ No Polyline or Polygon feature classes found.")


import arcpy
import os

# Set environment
arcpy.env.workspace = r"N:\EIAMS\GIS\Project_Map_Docs\IAM_QA_QC_ArcGIS_Pro_Project\Connection Files\GIS_DnD@sde2-(OS_Authenticate).sde"
arcpy.env.overwriteOutput = True

# Input feature class and output folder
in_fc = "Parking Lot Sector"
output_gdb = r"N:\Kabirr\Completed Assigned Tasks\True_Curves_Export_SDE\Densified_Output.gdb"

# Create output GDB if it doesn't exist
if not arcpy.Exists(output_gdb):
    arcpy.CreateFileGDB_management(os.path.dirname(output_gdb), os.path.basename(output_gdb))

# Field name for conservation area
conservation_area_field = 'Conservation_Area_Name'

# Temporary layer to select only true curved features
temp_layer = "curved_features_lyr"
arcpy.MakeFeatureLayer_management(in_fc, temp_layer)

# Build WHERE clause to select true curves
where_clause = "1=1"  # placeholder since we’re filtering programmatically

# List to track OBJECTIDs with curves
object_ids = []

# Get curved OBJECTIDs
with arcpy.da.SearchCursor(in_fc, ['OBJECTID', 'SHAPE@']) as cursor:
    for row in cursor:
        if row[1].hasCurves:
            object_ids.append(row[0])

# Filter layer to just those curved features
if object_ids:
    id_string = ",".join(map(str, object_ids))
    arcpy.SelectLayerByAttribute_management(temp_layer, "NEW_SELECTION", f"OBJECTID IN ({id_string})")

    # Export selected features to a new feature class
    curved_fc = os.path.join(output_gdb, in_fc.replace(" ", "_") + "_CurvedOnly")
    arcpy.CopyFeatures_management(temp_layer, curved_fc)

    print(f"✅ Exported {len(object_ids)} true curve features to:\n{curved_fc}")

    # Apply Densify to remove curves
    densified_fc = curved_fc.replace("_CurvedOnly", "_Densified")
    arcpy.Densify_edit(
        in_features=curved_fc,
        densification_method="DISTANCE",  # Options: DISTANCE | ANGLE | DISTANCE_AND_ANGLE
        distance="1 Meters",
        max_deviation="0.1 Meters"
    )

    print(f"📐 Applied densification to:\n{curved_fc}")

else:
    print("❌ No true curved features found to densify.")


import arcpy
import pandas as pd
import os

# Set workspace to feature dataset
arcpy.env.workspace = r"N:\EIAMS\GIS\Project_Map_Docs\IAM_QA_QC_ArcGIS_Pro_Project\GIS_Production@sde2_GIS_VIEWER.sde\PRODUCTION.IT.Infrastructure"

# Output Excel for true curves
output_excel = r"N:\Kabirr\Completed Assigned Tasks\Polygons_Polylines_Features.xlsx"

# Get all feature classes in the workspace
feature_classes = arcpy.ListFeatureClasses()

# Track curved features
curved_results = []

print("🔍 Scanning feature classes for Line and Polygon geometry types...\n")

for fc in feature_classes:
    desc = arcpy.Describe(fc)
    shape_type = desc.shapeType

    # Only process line or polygon geometries
    if shape_type.lower() in ["polygon", "polyline"]:
        print(f"📌 Processing: {fc} (Geometry: {shape_type})")

        # Search for true curves
        with arcpy.da.SearchCursor(fc, ['OBJECTID', 'SHAPE@']) as cursor:
            for row in cursor:
                object_id = row[0]
                geometry = row[1]
                if geometry and geometry.hasCurves:
                    curved_results.append({
                        'FeatureClass': fc,
                        'OBJECTID': object_id,
                        'GeometryType': shape_type
                    })
                    print(f"   ➤ Found true curve at OBJECTID {object_id}")

print("\n✅ Completed scanning.")

# Export to Excel if curved features were found
if curved_results:
    df = pd.DataFrame(curved_results)
    df.to_excel(output_excel, index=False)
    print(f"\n📤 Exported {len(curved_results)} curved features to:\n{output_excel}")
else:
    print("\n❌ No true curved features found in line or polygon feature classes.")


import arcpy
import pandas as pd

# Set workspace
arcpy.env.workspace = r"N:\EIAMS\GIS\Project_Map_Docs\IAM_QA_QC_ArcGIS_Pro_Project\GIS_Production@sde2_GIS_VIEWER.sde\PRODUCTION.IT.Infrastructure"

# Input feature class
in_fc = "PRODUCTION.IT.Parking_Lot_Sector"

# Output Excel path
output_excel = r"N:\Kabirr\Completed Assigned Tasks\True_Curves_Features.xlsx"

# Verify feature class
feature_count = int(arcpy.GetCount_management(in_fc).getOutput(0))
print(f"Total features: {feature_count}")
desc = arcpy.Describe(in_fc)
print(f"Geometry type: {desc.shapeType}")

# Container for curved features
curved_features = []

# Search for true curves
with arcpy.da.SearchCursor(in_fc, ['OBJECTID', 'SHAPE@']) as cursor:
    for row in cursor:
        object_id = row[0]
        geometry = row[1]
        if geometry and geometry.hasCurves:
            curved_features.append({'OBJECTID': object_id})
            print(f"Found true curve at OBJECTID {object_id}")

# Export results
if curved_features:
    df = pd.DataFrame(curved_features)
    df.to_excel(output_excel, index=False)
    print(f"✅ Exported {len(curved_features)} curved features to:\n{output_excel}")
else:
    print("❌ No features with true curves found.")
    print("Suggestion: Verify in ArcGIS Pro by editing a feature you expect to have a true curve.")


