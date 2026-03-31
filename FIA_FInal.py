import arcpy
import time

# Input and output settings
input_geodatabase = r"N:\EIAMS\GIS\Project_Map_Docs\Infrastructure_Flood_Analysis\FilteredInfrastructure.gdb"
output_geodatabase = r"N:\EIAMS\GIS\Project_Map_Docs\Infrastructure_Flood_Analysis\Flood_Impacted_Assets.gdb"

# Flood zone layer
flood_zone_layer = r"N:\EIAMS\GIS\Project_Map_Docs\Infrastructure_Flood_Analysis\MyProject12\MyProject12.gdb\Regulatoryand1_Dissolve"

# Set environment for overwriting outputs
arcpy.env.workspace = input_geodatabase
arcpy.env.overwriteOutput = True

# Create the output geodatabase if it doesn't exist
if not arcpy.Exists(output_geodatabase):
    arcpy.CreateFileGDB_management(r"N:\EIAMS\GIS\Project_Map_Docs\Infrastructure_Flood_Analysis", "Flood_Impacted_Assets.gdb")
    print(f"Geodatabase created: {output_geodatabase}")

# List all feature classes in the infrastructure dataset
all_feature_classes = arcpy.ListFeatureClasses()

# Print all feature classes found in the input geodatabase for debugging
print(f"All feature classes in {input_geodatabase}: {all_feature_classes}")

# Initialize the list to store intersected feature classes
intersected_feature_classes = []

# Get total number of feature classes for progress tracking
total_features = len(all_feature_classes)

# Iterate through each feature class and perform pairwise intersection with the flood zone layer
for index, fc in enumerate(all_feature_classes):
    # Define the input feature class and output feature class paths
    input_fc = f"{input_geodatabase}\\{fc}"
    output_fc = f"{output_geodatabase}\\{fc}_Flood_Impacted_Pairwise"
    
    # Display progress
    progress_percentage = ((index + 1) / total_features) * 100
    print(f"Processing {fc} ({index + 1}/{total_features}) - {progress_percentage:.2f}% complete")
    
    # Perform the pairwise intersection
    try:
        start_time = time.time()  # Record start time for this operation
        arcpy.analysis.PairwiseIntersect([input_fc, flood_zone_layer], output_fc)
        elapsed_time = time.time() - start_time  # Calculate elapsed time
        print(f"Output saved: {output_fc} (Time taken: {elapsed_time:.2f} seconds)")
        intersected_feature_classes.append(output_fc)  # Add to list only if successful
    except Exception as e:
        print(f"Failed to process {fc}: {str(e)}")

# Check if the intersected feature classes list is populated
if not intersected_feature_classes:
    print("No valid intersected feature classes to merge.")
else:
    print(f"Intersected feature classes: {intersected_feature_classes}")
    
    # Proceed with merging only if there are intersected feature classes
    merged_output_fc = f"{output_geodatabase}\\Infrastructure_Flood_Impact_Merged"
    print("Merging intersected feature classes into a single output...")
    
    try:
        arcpy.management.Merge(intersected_feature_classes, merged_output_fc)
        print(f"Merged output saved: {merged_output_fc}")
    except Exception as e:
        print(f"Failed to merge: {str(e)}")


import arcpy

# Set workspace and output settings
input_geodatabase = r"N:\EIAMS\GIS\Project_Map_Docs\Infrastructure_Flood_Analysis\Flood_Impacted_Assets.gdb"
output_geodatabase = r"N:\EIAMS\GIS\Project_Map_Docs\Infrastructure_Flood_Analysis\Flood_Impacted_Assets.gdb"

# Ensure the output geodatabase exists, or create it
if not arcpy.Exists(output_geodatabase):
    arcpy.CreateFileGDB_management(r"N:\EIAMS\GIS\Project_Map_Docs\Infrastructure_Flood_Analysis", "Flood_Impacted_Assets.gdb")
    print(f"Output geodatabase created: {output_geodatabase}")

# Define output paths for different geometry types
output_polygon_fc = f"{output_geodatabase}\\Flood_Impacted_Assets_Polygon"
output_point_fc = f"{output_geodatabase}\\Flood_Impacted_Assets_Point"
output_line_fc = f"{output_geodatabase}\\Flood_Impacted_Assets_Line"

# Set the workspace
arcpy.env.workspace = input_geodatabase
arcpy.env.overwriteOutput = True

# List all feature classes ending with '_Flood_Impact'
all_flood_impact_layers = [fc for fc in arcpy.ListFeatureClasses() if fc.endswith('_Flood_Impacted_Pairwise')]

# Separate layers by geometry type
point_layers = []
line_layers = []
polygon_layers = []

for fc in all_flood_impact_layers:
    desc = arcpy.Describe(fc)
    if desc.shapeType == "Point":
        point_layers.append(fc)
    elif desc.shapeType == "Polyline":
        line_layers.append(fc)
    elif desc.shapeType == "Polygon":
        polygon_layers.append(fc)

# Merge layers by geometry type
if point_layers:
    arcpy.management.Merge(point_layers, output_point_fc)
    print(f"Merged point feature classes into: {output_point_fc}")
else:
    print("No point feature classes to merge.")

if line_layers:
    arcpy.management.Merge(line_layers, output_line_fc)
    print(f"Merged line feature classes into: {output_line_fc}")
else:
    print("No line feature classes to merge.")

if polygon_layers:
    arcpy.management.Merge(polygon_layers, output_polygon_fc)
    print(f"Merged polygon feature classes into: {output_polygon_fc}")
else:
    print("No polygon feature classes to merge.")



