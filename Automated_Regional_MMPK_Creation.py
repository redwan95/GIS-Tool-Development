import arcpy

test_path = r"N:\EIAMS\GIS\Project_Map_Docs\Disaster_Assessment\sde2.sde\PRODUCTION.IT.Boundaries\PRODUCTION.IT.MDC_Lands"
if arcpy.Exists(test_path):
    print("✅ Area of Interest feature class found.")
else:
    print("❌ Area of Interest feature class NOT found.")


import arcpy
import os
from datetime import datetime

# =========================================================
# Configuration
# =========================================================

# Base output folder for MMPKs
output_folder = r"N:\EIAMS\GIS\Project_Map_Docs\Disaster_Assessment\MMPK_Update_March_2025\Redwan_Testing_2"

# Ensure output folder exists
if not os.path.exists(output_folder):
    os.makedirs(output_folder)

# Common parameters
area_of_interest = r"N:\EIAMS\GIS\Project_Map_Docs\Disaster_Assessment\sde2.sde\PRODUCTION.IT.Boundaries\PRODUCTION.IT.MDC_Lands"
extent = "DEFAULT"
clip_features = "SELECT"

summary = (
    "This MMPK is used as part of the disaster damage response effort. "
    "It contains geospatial infrastructure data from the GIS_DnD geodatabase production environment."
)

description = (
    "This MMPK contains feature classes from the GIS_DnD geodatabase production environment. "
    "This MMPK is used for Emergency Incident Command damage record collection. "
    "When a feature is selected in the Field Maps application, the pop-up has a clickable HTML header. "
    "When the header is selected, it launches the Survey123 application and the associated Damage Assessment survey. "
    "HTML configuration allows the survey to be populated with attribute information from the associated feature. "
    "This MMPK requires frequent updates to ensure that additions and removals of infrastructure assets are accurately represented."
)

tags = "MO, Missouri, Missouri Department of Conservation, Infrastructure Management Branch (IM)"
credits = "Missouri Department of Conservation, Infrastructure Management"

use_limitations = (
    "Although all data in this data set have been compiled by the Missouri Department of Conservation, "
    "no warranty, expressed or implied, is made by the department as to the accuracy of the data and related materials. "
    "The act of distribution shall not constitute any such warranty, and no responsibility is assumed by the department "
    "in the use of these data or related materials."
)

# List of region names (must match ArcGIS Pro map names exactly)
regions = [
    'Southeast',
    'Ozark',
    'St Louis',
    'Central',
    'Kansas City',
    'Northeast',
    'Northwest',
    'Southwest',
]

# Load ArcGIS Project
aprx = arcpy.mp.ArcGISProject("CURRENT")

# Timestamp for output filenames
date_stamp = datetime.now().strftime("%Y%m%d_%H%M")

# =========================================================
# Step 1: Verify that all map frames exist
# =========================================================
print("Checking for existing maps in ArcGIS Pro project...\n")

map_names_in_project = [m.name for m in aprx.listMaps()]
missing_maps = []

for region in regions:
    expected_map_name = f"{region} - Field Damage Assessment"
    if expected_map_name not in map_names_in_project:
        print(f"❌ MISSING: {expected_map_name}")
        missing_maps.append(expected_map_name)
    else:
        print(f"✅ FOUND: {expected_map_name}")

# Stop here if all maps are missing
if len(missing_maps) == len(regions):
    raise RuntimeError("❌ No valid map frames found. Please check your ArcGIS Pro project.")

# =========================================================
# Step 2: Create MMPKs for valid maps
# =========================================================
print("\nStarting MMPK creation for available regions...\n")

for region in regions:
    in_map = f"{region} - Field Damage Assessment"

    # Skip missing maps
    if in_map in missing_maps:
        print(f"⏭️ SKIPPED: {in_map} (Map not found in project)")
        continue

    title = in_map
    output_file = os.path.join(output_folder, f"{region.replace(' ', '_')}_{date_stamp}.mmpk")

    print(f"\n===================================")
    print(f"Creating MMPK for: {region}")
    print(f"Output file: {output_file}")
    print("===================================\n")

    try:
        # Attempt to create the mobile map package
        arcpy.management.CreateMobileMapPackage(
            in_map=in_map,
            output_file=output_file,
            in_locator=None,
            area_of_interest=area_of_interest,
            extent=extent,
            clip_features=clip_features,
            title=title,
            summary=summary,
            description=description,
            tags=tags,
            credits=credits,
            use_limitations=use_limitations,
            anonymous_use="STANDARD",
            enable_map_expiration="DISABLE_MAP_EXPIRATION",
            map_expiration_type="ALLOW_TO_OPEN",
            expiration_date=None,
            expiration_message="This map is expired. Contact the map publisher for an updated map.",
            select_related_rows="KEEP_ALL_RELATED_ROWS",
            reference_online_content="EXCLUDE_SERVICE_LAYERS"
        )

        print(f"✅ SUCCESS: MMPK created for {region}")

    except Exception as e:
        # Catch errors and continue to the next map
        print(f"❌ ERROR creating MMPK for {region}: {e}")

print("\nProcessing complete!")
