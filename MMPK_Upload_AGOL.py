import os
import csv
from arcgis.gis import GIS
from datetime import datetime



# -------------------------------
# Parameters
# -------------------------------
mmpk_folder = r"N:\EIAMS\GIS\Project_Map_Docs\Disaster_Assessment\MMPK_Update_March_2025\Redwan_Testing_3"
log_file = os.path.join(mmpk_folder, "upload_log.csv")
upload_folder_name = "Operational_Disaster_MMPKs"
backup_folder_name = "Backup_MMPK"
regions = [
    "St_Louis", "Central", "Kansas_City", "Northeast",
    "Northwest", "Southeast", "Southwest", "Ozark"
]

# -------------------------------
# Connect to ArcGIS Pro session
# -------------------------------
gis = GIS("pro")
print("Logged in as:", gis.users.me.username)

# -------------------------------
# Ensure AGOL folders exist
# -------------------------------
for folder_name in [upload_folder_name, backup_folder_name]:
    if folder_name not in [f['title'] for f in gis.users.me.folders]:
        gis.users.me.create_folder(folder_name)
        print(f"Created folder in AGOL: {folder_name}")

# -------------------------------
# Create CSV log if not exists
# -------------------------------
if not os.path.exists(log_file):
    with open(log_file, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Region", "Uploaded File Name", "Uploaded Item ID",
                         "Backup Item ID", "Local File Path"])

# -------------------------------
# Helper: Find existing item by region and folder
# -------------------------------
def find_item_by_region(region_name, folder_name, is_backup=False):
    if is_backup:
        # Search for backup items (title starts with region_name - Field Damage Assessment)
        search_title = f"{region_name} - Field Damage Assessment"
        items = gis.content.search(
            query=f'title:"{search_title}*" AND owner:{gis.users.me.username}',
            item_type="Mobile Map Package", max_items=10
        )
    else:
        search_title = f"{region_name} - Field Damage Assessment"
        items = gis.content.search(
            query=f'title:"{search_title}" AND owner:{gis.users.me.username}',
            item_type="Mobile Map Package", max_items=10
        )
    # Filter by folder
    folder_id = next((f['id'] for f in gis.users.me.folders if f['title'] == folder_name), None)
    for item in items:
        if item.ownerFolder == folder_id:
            return item
    return None

# -------------------------------
# Helper: Get next version number for backup
# -------------------------------
def get_next_version(region_name):
    items = gis.content.search(
        query=f'title:"{region_name} - Field Damage Assessment*" AND owner:{gis.users.me.username}',
        item_type="Mobile Map Package", max_items=100
    )
    backup_folder_id = next((f['id'] for f in gis.users.me.folders if f['title'] == backup_folder_name), None)
    versions = []  # Collect existing versions
    for item in items:
        if item.ownerFolder == backup_folder_id:
            title = item.title
            if "_V" in title:
                try:
                    version = int(title.split("_V")[-1].split("_")[0])
                    versions.append(version)
                except ValueError:
                    continue
    return max(versions) + 1 if versions else 1  # Start at V1 if none found

# -------------------------------
# Main process
# -------------------------------
for filename in os.listdir(mmpk_folder):
    if not filename.lower().endswith(".mmpk"):
        continue

    mmpk_path = os.path.join(mmpk_folder, filename)

    # Detect region
    region_found = next((r for r in regions if r.lower() in filename.lower()), None)
    if not region_found:
        print(f"⚠️ Skipping file (region not found in filename): {filename}")
        continue

    # Define upload title
    upload_title = f"{region_found} - Field Damage Assessment"

    # -------------------------------
    # Backup existing Operational MMPK
    # -------------------------------
    existing_operational = find_item_by_region(region_found, upload_folder_name)
    backup_item_id = ""
    if existing_operational:
        # Delete existing backup if it exists
        existing_backup = find_item_by_region(region_found, backup_folder_name, is_backup=True)
        if existing_backup:
            try:
                existing_backup.delete()
                print(f"🗑️ Deleted old backup: {existing_backup.title}")
            except Exception as e:
                print(f"⚠️ Could not delete old backup: {existing_backup.title} — {e}")

        # Create new backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = get_next_version(region_found)
        backup_title = f"{upload_title}_V{version}_{timestamp}"
        try:
            existing_operational.update({"title": backup_title})
            existing_operational.move(backup_folder_name)
            backup_item_id = existing_operational.id
            print(f"🟡 Backup created: {backup_title} (ID: {backup_item_id})")
        except Exception as e:
            print(f"⚠️ Failed to backup {existing_operational.title}: {e}")
            continue

    # -------------------------------
    # Check and delete conflicting filename in upload folder (FIXED)
    # -------------------------------
    try:
        upload_folder = next((f for f in gis.users.me.folders if f['title'] == upload_folder_name), None)
        if upload_folder:
            folder_items = gis.users.me.items(folder=upload_folder)
            basename = os.path.basename(mmpk_path)
            for item in folder_items:
                if item.type == "Mobile Map Package" and item.name == basename:
                    print(f"🗑️ Deleting conflicting item with filename '{basename}': {item.title} (ID: {item.id})")
                    item.delete()
        else:
            print(f"⚠️ Upload folder '{upload_folder_name}' not found.")
    except Exception as e:
        print(f"⚠️ Failed to check/delete conflicting items: {e}")

    # -------------------------------
    # Upload new MMPK
    # -------------------------------
    try:
        item_properties = {
            "title": upload_title,
            "type": "Mobile Map Package",
            "tags": ["Disaster", "MMPK"]
        }
        uploaded_item = gis.content.add(
            item_properties=item_properties,
            data=mmpk_path,
            folder=upload_folder_name
        )
        print(f"✅ Uploaded: {uploaded_item.title} (ID: {uploaded_item.id})")

        # -------------------------------
        # Log activity
        # -------------------------------
        with open(log_file, mode='a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                datetime.now().date(),
                region_found,
                upload_title,
                uploaded_item.id,
                backup_item_id,
                mmpk_path
            ])

    except Exception as e:
        print(f"❌ Failed to upload {filename}: {e}")

print(f"\n✅ All MMPKs processed. Upload log saved at: {log_file}")


