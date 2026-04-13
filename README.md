
# CAD to GIS Automation Tool

## Executive Summary
The CAD to GIS Automation Tool is an enterprise-grade Python-based application designed for the Missouri Department of Conservation (MDC) to streamline the conversion of AutoCAD DWG files into ArcGIS Geodatabases (GDB) with automated schema mapping and quality control (QA/QC) workflows. This tool directly addresses MDC's infrastructure documentation and asset management needs by enabling rapid, accurate digitization of CAD-based civil engineering designs into production GIS systems.

## 🎯 Business Value

This tool was built to solve common pain points in infrastructure GIS data management:

- **Accelerates data ingestion** of civil engineering drawings (roads, water, sewer, stormwater, etc.)
- **Reduces manual digitizing time** by directly reading DWG geometry and attributes
- **Supports dual workflows**:
  - Quick raw exports for exploration and QC
  - Schema-mapped loading for official production datasets
- **Ensures data quality** through detailed previews, spatial reference validation, and field mapping visibility
- **Provides full auditability** with session history, timestamped logs, and exportable log files
- **Improves naming consistency** with intelligent project-based geodatabase and feature class naming

---

## ✨ Key Features

### Core Capabilities

- **📂 Smart Folder Scanning** – Automatically detects and lists all DWG files
- **📦 One-Click Temp GDB Creation** – Creates consistently named project geodatabases (`Project_86-12-12_temp.gdb`)
- **🔎 Rich Preview System** – Shows feature counts, spatial reference, extent, fields, and sample data before processing
- **Three Processing Modes**:

  | Button | Purpose | Best For |
  |--------|-------|---------|
  | **📄 Export Full DWG** | Exports *all* polylines from the entire DWG (no layer selection needed) | Bulk ingestion, initial data review |
  | **📦 Export Raw Layer** | Exports selected layer(s) with all original DWG attributes | Detailed QC and attribute preservation |
  | **🚀 Digitize (Schema)** | Maps data to an SDE production schema template | Official data loading into enterprise GIS |

### Additional Features

- Automatic coordinate system projection when needed
- Append vs. Overwrite options
- One-click addition of results to the active map
- Complete session history and log export
- Robust error handling and user-friendly logging
- Support for both hyphenated and numeric project numbers

---

## 🛠️ How to Use

### Quick Start

1. **Enter Project Number** → Click **"📦 Create Temp GDB"**
2. **Scan or update** the DWG folder location
3. **Select** a DWG file → Feature Type (Polyline, Point, etc.) → CAD Layer
4. Choose your desired output mode:
   - Use **📄 Export Full DWG** for fastest results (recommended starting point)
   - Use **🚀 Digitize (Schema)** when loading into official SDE templates

---

## 📋 Workflow Summary

1. **Source Configuration** – Define project and DWG folder
2. **DWG Exploration** – Browse geometry types and CAD layers with rich previews
3. **Output Configuration** – Select target schema (for schema mode) and output GDB
4. **Execution** – Run one of the three export options
5. **Documentation** – Review log and export session history

---

## 🔧 Technical Details

- Built with **ArcPy** and **ipywidgets**
- Runs in **ArcGIS Pro** (Notebook environment)
- Reads DWG files directly via ArcGIS Pro’s CAD engine
- Supports enterprise geodatabases (SDE) for schema templates
- Preserves original DWG attributes (`Layer`, `Color`, `Linetype`, `Elevation`, etc.)


## Technical Architecture
The tool operates on a modular architecture, integrating with existing CAD and GIS software. It employs robust algorithms for file conversion and includes error-checking mechanisms to ensure data integrity.

## Business Outcomes
- Decreased project lead times.
- Increased accuracy in GIS data representation.
- Improved collaboration across departments.

## ROI Analysis
Investing in this tool leads to significant cost savings by minimizing manual data entry and rework. The reduction in project turnaround times translates to better resource allocation and increased productivity.


📋 System Requirements
- Environment: ArcGIS Pro 2.9+ / 3.x
- Permissions: Read access to CAD folders and Write access to the specified Output GDB path.
- License: Basic, Standard, or Advanced (Tool checks for Spatial/3D extensions automatically).

## Setup & Usage
1. Install the tool following the provided installation guide.
2. Launch the application and configure settings as per your project requirements.
3. Import CAD files and initiate conversion process.
4. Export the converted files to the desired GIS formats.

## Future Enhancements
- Integration with cloud services for real-time collaboration.
- Expansion of supported CAD formats.
- Enhanced data visualization features to aid in decision-making.


# 🛠️ DWG → GDB Digitization Tool (User Guide)

## 🎯 What This Tool Does
This tool helps you convert **AutoCAD (.DWG) files** into **GIS feature classes** in ArcGIS Pro.

You can:
- 📄 Export the **entire DWG (all polylines)**
- 📦 Export a **specific CAD layer with original attributes**
- 🚀 Convert CAD data into a **standard GIS schema (SDE template)**

---

## 🧑‍💻 Who Can Use This?
✔ Non-technical users  
✔ CAD designers  
✔ GIS beginners  
✔ Anyone working with DWG files  

---

## 📝 Inputs You Need to Provide

### 1️⃣ Project Number
- Example: `86-12-12` or `86121200`
- Used to create a temporary working geodatabase

---

### 2️⃣ DWG Folder
- Folder where your `.dwg` files are stored
- Example:
    

---

### 3️⃣ Select DWG File
- Choose your CAD file from dropdown

---

### 4️⃣ Feature Type
- Example: Polyline, Point, Polygon
- Usually: **Polyline**

---

### 5️⃣ CAD Layer
- Select a specific layer (e.g., WATER, ROAD, etc.)
- OR choose:
- **ALL LAYERS** (exports everything)

---

### 6️⃣ Output GDB
- Where the GIS data will be saved
- Auto-filled if you click:
👉 **📦 Create Temp GDB**

---

### 7️⃣ Output Feature Class Name
- Name of your output layer
- Example:
    

---

## ⚡ Actions You Can Perform

### 📄 Export Full DWG (EASIEST)
✔ One-click solution  
✔ No need to select layer or schema  
✔ Exports ALL polylines  

👉 Use this if:
- You want **everything from the DWG**
- You don’t need schema mapping

---

### 📦 Export Raw Layer
✔ Exports selected CAD layer  
✔ Keeps original DWG attributes  

👉 Use this if:
- You want **specific layers only**
- You need CAD attributes like Layer, Color, etc.

---

### 🚀 Digitize (Schema)
✔ Converts CAD → GIS schema  
✔ Matches SDE database structure  

👉 Use this if:
- You are preparing **production GIS data**
- You need **standardized fields**

---

## 🔁 Simple Workflow (Recommended)

1. Enter **Project Number**
2. Click **📦 Create Temp GDB**
3. Select **DWG File**
4. Choose **📄 Export Full DWG** (quickest)

---

## 💡 Tips

- ✔ Use **Export Full DWG** for fastest results  
- ✔ Use **Raw Layer** for layer-specific extraction  
- ✔ Use **Digitize (Schema)** for final GIS datasets  
- ✔ Check preview before running  

---

## ⚠️ Common Issues

- ❌ No features found → Check layer selection  
- ❌ SDE not loading → Click “Reload SDE”  
- ❌ Output GDB missing → Create Temp GDB  

---

## ✅ Output

You will get:
- A feature class inside your GDB
- GIS-ready data
- Optional map layer (if enabled)

---
