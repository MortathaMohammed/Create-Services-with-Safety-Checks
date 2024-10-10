# **Automated Service Creation for Inpatient Records in ERPNext Healthcare**

This repository contains scripts that automate the creation of service documents (Medication Request, Lab Test, Clinical Procedure) based on entries in the **Inpatient Record**'s child tables in ERPNext Healthcare. It also includes a duplicate check mechanism to prevent the creation of duplicate services.

## **Overview**

In ERPNext Healthcare, managing services prescribed to patients during inpatient care can be time-consuming. This script automates the creation of service documents when an **Inpatient Record** is saved. It processes new entries in the child tables for medications, lab tests, and procedures, and creates the corresponding service documents.

Additionally, it includes a duplicate checking mechanism to prevent the creation of services that already exist for the patient.

## **Configuration**

### **1. Add `custom_linked_document` Field**

To enable the script to link created service documents back to the child table entries, you need to add a custom field named `custom_linked_document` to each of the following child doctypes:

- **Drug Prescription**
- **Lab Prescription**
- **Procedure Prescription**

**Steps to Add the Field:**

1. **Navigate to Customize Form:**

   - Go to **Desk > Customization > Customize Form**.

2. **Select the Child Doctype:**

   - In the **Enter Form Type** field, enter one of the child doctype names (e.g., `Drug Prescription`).

3. **Add a New Field:**

   - Scroll down to the **Fields** section.
   - Click on **Add Row** at the bottom.

4. **Set Field Properties:**

   - **Label**: `Custom Linked Document`
   - **Field Name**: `custom_linked_document`
   - **Field Type**: `Data` (or `Link` if you want to link to the specific service doctype)
   - **Options**: If Field Type is `Link`, set to the corresponding service doctype (e.g., `Medication Request`).
   - **In List View**: Check this option to display the field in the child table grid.
   - **Read Only**: Check this option to prevent manual editing.
   - **Mandatory**: Leave unchecked.
   - **Hidden**: Leave unchecked.

5. **Save the Customization:**

   - Click **Update** to save the changes.

6. **Repeat for Other Child Doctypes:**

   - Repeat steps 2-5 for `Lab Prescription` and `Procedure Prescription`.

### **2. Client Script**

Add the following client script to the **Inpatient Record** doctype:

1. **Navigate to Custom Script:**

   - Go to **Desk > Customization > Custom Script**.

2. **Create a New Custom Script:**

   - If not already present, click **Add Custom Script**.
   - Set **Doctype** to `Inpatient Record`.

3. **Paste the Script:**

   - client_script_for_inpatient_handler.js

4. **Save the Script:**

   - Click **Save**.

### **3. Server Script**

Create a Python file in your custom app to handle the server-side logic.

1. **Create `inpatient_handler.py` in Your App:**

   - File path: `~/frappe-bench/apps/custom_app/custom_app/inpatient_handler.py`

2. **Paste the Following Code:**

   - inpatient_handler.py

3. **Save the File:**

   - Ensure the file is saved and properly indented.

### **4. Event Hook**

Add the event hook in your app's `hooks.py` file to trigger the `create_services` function after an Inpatient Record is saved.

1. **Open `hooks.py`:**

   - File path: `~/frappe-bench/apps/custom_app/custom_app/hooks.py`

2. **Add the Following Entry:**

   ```python
   doc_events = {
       "Inpatient Record": {
           "after_save": "custom_app.inpatient_handler.create_services"
       }
   }
   ```

   - Ensure that the module path (`custom_app.inpatient_handler.create_services`) matches your app's structure.

3. **Restart Bench:**

   ```bash
   bench restart
   ```

   - This ensures that the changes in `hooks.py` are applied.

---

## **Usage**

1. **Create or Open an Inpatient Record:**

   - Go to **Healthcare > Inpatient > Inpatient Record**.
   - Create a new record or open an existing one.

2. **Add Entries to Child Tables:**

   - **Medications:** Add entries in the **Drug Prescription** table.
   - **Lab Tests:** Add entries in the **Lab Test Prescription** table.
   - **Procedures:** Add entries in the **Procedure Prescription** table.

3. **Save the Inpatient Record:**

   - When you save, the client script will check for duplicates.
   - If duplicates are found, you'll be prompted to confirm whether to create them again.
   - Upon confirmation, the server script will create the corresponding service documents.

4. **Check Linked Documents:**

   - The `custom_linked_document` field in each child table entry will be updated with the name of the created service document.
   - You can view the linked documents directly from the child table.

---

### **5. Adding `create_service_request_for_service` Method**

The `create_service_request_for_service` method is used to create a Service Request for each service generated (Medication Request, Lab Test, Clinical Procedure). This method is essential to ensure that each generated service has an associated Service Request that tracks its status and related details.

#### **Method Description**

- **Method Name**: `create_service_request_for_service`
- **Purpose**: Creates a Service Request document for a given service type and name, linking it to the corresponding **Inpatient Record**.

#### **Method Code**

```python
def create_service_request_for_service(doc, service_doctype, service_name, service_type):
    try:
        # Determine the current date and time
        from datetime import datetime
        now = datetime.now()
        order_date = now.date()
        order_time = now.time().strftime("%H:%M:%S")

        # Get the correct status Code Value document name
        status_code_value = frappe.get_value("Code Value", {"code_value": "active"}, "name")
        if not status_code_value:
            frappe.throw(_("Could not find a valid status with code value 'active'."))

        # Populate the Service Request document with mandatory fields
        service_request = frappe.get_doc({
            "doctype": "Service Request",
            "naming_series": "HSR-",
            "order_date": order_date,
            "order_time": order_time,
            "status": status_code_value,
            "company": doc.company or frappe.defaults.get_user_default("Company"),
            "patient": doc.patient,
            "practitioner": doc.primary_practitioner,
            "template_dt": service_doctype,
            "template_dn": service_name
        })

        # Insert the Service Request
        service_request.insert(ignore_permissions=True)
        frappe.logger().info(
            f"Service Request '{service_request.name}' created for {service_doctype} '{service_name}'"
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _(f"Error creating Service Request"))
        frappe.throw(_(f"An error occurred while creating the Service Request for {service_name}: {str(e)}"))
```

- **Parameters**:
  - `doc`: The **Inpatient Record** document triggering the service creation.
  - `service_doctype`: The type of service (e.g., `"Medication Request"`).
  - `service_name`: The name of the service document.
  - `service_type`: The category of service (e.g., `"Medication"`).

- **Functionality**:
  - The method populates the mandatory fields for the **Service Request**.
  - It assigns the `status` from a **Code Value** record, ensuring it matches an existing linked value in the system.
  - Inserts the newly created **Service Request** into the database.

---

## **Code Explanation**

### **Client Script**

- **Purpose:** Runs on the client side (browser) and intercepts the save action to perform duplicate checks before services are created.

- **Key Functions:**
  - **before_save:** Collects new entries from child tables and checks for duplicates.
  - **collect_services:** Gathers services that need to be checked or created.
  - **check_duplicates_and_proceed:** Calls a server-side function to check for existing services and prompts the user accordingly.

- **Important Variables:**
  - `frm.is_duplicate_check_performed`: A flag to prevent duplicate checks if they've already been performed.
  - `services_to_check`: An array of service entries that need to be checked for duplicates.

### **Server Script**

- **Purpose:** Runs on the server side and handles the creation of service documents and duplicate checking.

- **Key Functions:**
  - **create_services:** Main function triggered after saving the Inpatient Record; processes medications, lab tests, and procedures.
  - **process_medications / process_lab_tests / process_procedures:** Process entries in each respective child table and create service documents.
  - **check_duplicate_services:** Checks if services already exist for the patient to prevent duplicates.

- **Error Handling:**
  - Errors encountered during service creation are collected in the `errors` list and displayed to the user.

---

## **Troubleshooting**

- **Services Not Created:**
  - Ensure that the `custom_linked_document` field exists in each child doctype.
  - Confirm that the event hook in `hooks.py` is correctly set up and that the bench has been restarted.
  - Check server logs for any errors using `bench --site your_site_name logs`.

- **Duplicate Check Not Working:**
  - Verify that the method path in `frappe.call` within the client script matches the server script's function path.
  - Ensure the server-side function `check_duplicate_services` is properly whitelisted with `@frappe.whitelist()`.

- **Fields Not Updated:**
  - Make sure that `custom_linked_document` is included in the child table's fields and is not hidden.
  - Check that `db_update()` is called after setting `custom_linked_document`.
  
---

**Note:** Replace `yourusername`, `yourrepository`, `your_site_name`, and other placeholders with your actual information.

If you have any questions or need further assistance, feel free to open an issue or contact the repository maintainer.
