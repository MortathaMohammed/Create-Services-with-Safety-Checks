import frappe
import json
from frappe import _

def create_services(doc, method=None):
    """
    Creates services (Medication Request, Lab Test, Clinical Procedure) based on new entries
    in the Inpatient Record's child tables. Only processes entries that have not yet been linked
    to a created service (i.e., where 'custom_linked_document' is not set).
    This function is triggered after the Inpatient Record is saved, but only if the patient is admitted.
    """
    frappe.logger().info(f"Starting service creation for Inpatient Record: {doc.name}")

    if doc.status != "Admitted":
        frappe.logger().info(_("No services will be created as the patient is not admitted."))
        return

    errors = []
    service_created = False  

    if process_medications(doc, errors):
        service_created = True
    if process_lab_tests(doc, errors):
        service_created = True
    if process_procedures(doc, errors):
        service_created = True

    if errors:
        error_messages = "\n".join(errors)
        frappe.msgprint(
            _("Errors occurred while creating services:\n{0}").format(error_messages),
            title=_("Service Creation Errors"),
            indicator="red"
        )
    elif service_created:
        frappe.msgprint(
            _("Services have been successfully created and corresponding Service Requests have been generated."),
            title=_("Service Creation"),
            indicator="green"
        )

def process_medications(doc, errors):
    service_created = False  # Track if a service was created
    if hasattr(doc, 'drug_prescription'):
        for medication in doc.drug_prescription:
            if not medication.custom_linked_document:
                try:
                    medication_name = medication.drug_name
                    dosage_form = medication.dosage_form
                    dosage = medication.dosage

                    # Create a new Medication Request
                    new_medication = frappe.get_doc({
                        "doctype": "Medication Request",
                        "patient": doc.patient,
                        "inpatient_record": doc.name,
                        "medication_item": medication_name,
                        "practitioner": doc.primary_practitioner,
                        "dosage_form": dosage_form,
                        "dosage": dosage,
                    })
                    new_medication.insert(ignore_permissions=True)
                    frappe.logger().info(
                        f"Medication Request '{new_medication.name}' created for medication '{medication_name}'"
                    )

                    # Update the child table entry and save
                    medication.custom_linked_document = new_medication.name
                    medication.db_update()

                    # Create a Service Request for this Medication Request
                    create_service_request_for_service(
                        doc=doc,
                        service_doctype="Medication Request",
                        service_name=new_medication.name,
                        service_type=doc.admission_service_unit_type
                    )

                    service_created = True  # Mark that a service was created

                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), _("Error creating Medication Request"))
                    errors.append(f"Medication '{medication_name}': {str(e)}")
            else:
                frappe.logger().debug(
                    f"Medication '{medication.drug_name}' already linked to {medication.custom_linked_document}"
                )
    return service_created

def process_lab_tests(doc, errors):
    service_created = False  # Track if a service was created
    service_unit = doc.inpatient_occupancies[0].service_unit
    if hasattr(doc, 'lab_test_prescription'):
        for lab_test in doc.lab_test_prescription:
            if not lab_test.custom_linked_document:
                try:
                    lab_test_code = lab_test.lab_test_code
                    patient_sex = doc.gender or "Other"
                    
                    # Create a new Lab Test
                    new_lab_test = frappe.get_doc({
                        "doctype": "Lab Test",
                        "patient": doc.patient,
                        "inpatient_record": doc.name,
                        "template": lab_test_code,
                        "patient_sex": patient_sex,
                        "service_unit": service_unit,
                        "practitioner": doc.primary_practitioner,
                        "status": "Draft"
                    })
                    new_lab_test.insert(ignore_permissions=True)

                    # Update the child table entry and save
                    lab_test.custom_linked_document = new_lab_test.name
                    lab_test.db_update()

                    frappe.logger().info(
                        f"Lab Test '{new_lab_test.name}' created for template '{lab_test_code}'"
                    )

                    # Create a Service Request for this Lab Test
                    create_service_request_for_service(
                        doc=doc,
                        service_doctype="Lab Test",
                        service_name=new_lab_test.name,
                        service_type=doc.admission_service_unit_type
                    )

                    service_created = True  # Mark that a service was created

                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), _("Error creating Lab Test"))
                    errors.append(f"Lab Test '{lab_test_code}': {str(e)}")
            else:
                frappe.logger().debug(
                    f"Lab Test '{lab_test.lab_test_code}' already linked to {lab_test.custom_linked_document}"
                )
    return service_created

def process_procedures(doc, errors):
    service_created = False  # Track if a service was created
    if hasattr(doc, 'procedure_prescription'):
        for procedure in doc.procedure_prescription:
            if not procedure.custom_linked_document:
                try:
                    procedure_name = procedure.procedure_name

                    # Create a new Clinical Procedure
                    new_procedure = frappe.get_doc({
                        "doctype": "Clinical Procedure",
                        "patient": doc.patient,
                        "inpatient_record": doc.name,
                        "procedure_template": procedure_name,
                        "status": "Draft"
                    })
                    new_procedure.insert(ignore_permissions=True)

                    # Update the child table entry and save
                    procedure.custom_linked_document = new_procedure.name
                    procedure.db_update()

                    frappe.logger().info(
                        f"Clinical Procedure '{new_procedure.name}' created for procedure '{procedure_name}'"
                    )

                    # Create a Service Request for this Clinical Procedure
                    create_service_request_for_service(
                        doc=doc,
                        service_doctype="Clinical Procedure",
                        service_name=new_procedure.name,
                        service_type=doc.admission_service_unit_type,
                    )

                    service_created = True  # Mark that a service was created

                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), _("Error creating Clinical Procedure"))
                    errors.append(f"Procedure '{procedure_name}': {str(e)}")
            else:
                frappe.logger().debug(
                    f"Procedure '{procedure.procedure_name}' already linked to {procedure.custom_linked_document}"
                )
    return service_created

def create_service_request_for_service(doc, service_doctype, service_name, service_type):
    try:
        # Determine the current date and time
        from datetime import datetime
        now = datetime.now()
        order_date = now.date()
        order_time = now.time().strftime("%H:%M:%S")

        # Get the correct status Code Value document name
        status_code_value = frappe.get_value("Code Value", {"code_value": "Draft"}, "name")
        if not status_code_value:
            frappe.throw(_("Could not find a valid status with code value 'Draft'."))

        # Populate the Service Request document with mandatory fields
        service_request = frappe.get_doc({
            "doctype": "Service Request",
            "naming_series": "HSR-",
            "order_date": order_date,
            "order_time": order_time,
            "status": status_code_value,  # Use the correct linked name here
            "company": doc.company or frappe.defaults.get_user_default("Company"),
            "patient": doc.patient,
            "practitioner": doc.primary_practitioner,
            "template_dt": service_doctype,
            "template_dn": service_name,
            "healthcare_service_unit_type": service_type,
            "source_doc": doc.doctype,
            "referred_to_practitioner": doc.secondary_practitioner,
            "expected_date": doc.expected_discharge,
            "patient_care_type": "Diagnostic",
            "occurrence_date": order_date
        })

        # Insert the Service Request
        service_request.insert(ignore_permissions=True)
        service_request.save()
        service_request.submit()
        frappe.logger().info(
            f"Service Request '{service_request.name}' created for {service_doctype} '{service_name}'"
        )

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), _("Error creating Service Request"))
        frappe.throw(_("An error occurred while creating the Service Request for {0}: {1}").format(service_name, str(e)))

def create_specimen_for_grouped_tests(doc):
    """
    This function handles adding grouped lab tests to the specimen after the document is saved.
    It generates a new specimen if no sample name is provided.
    """
    sample_name = doc.sample_name if doc.sample_name else "Unknown Sample"

    new_specimen = frappe.get_doc({
        "doctype": "Specimen",
        "patient": doc.patient,
        "sample_name": sample_name,
        "lab_tests": [test.name for test in doc.lab_tests],
        "status": "Collected"
    })

    new_specimen.insert(ignore_permissions=True)
    frappe.msgprint(f"New Specimen '{new_specimen.name}' created with sample name '{sample_name}'.")


@frappe.whitelist()
def check_duplicate_services(patient, services):
    duplicates = []
    # Deserialize 'services' if it's a string
    if isinstance(services, str):
        services = json.loads(services)
    
    for service in services:
        service_type = service.get('service_type')
        service_name = service.get('service_name')

        if service_type == 'Medication':
            existing = frappe.get_all('Medication Request', filters={
                'patient': patient,
                'medication_item': service_name,
                'docstatus': ['<', 2]
            }, limit=1)
        elif service_type == 'Lab Test':
            existing = frappe.get_all('Lab Test', filters={
                'patient': patient,
                'template': service_name,
                'docstatus': ['<', 2]
            }, limit=1)
        elif service_type == 'Procedure':
            existing = frappe.get_all('Clinical Procedure', filters={
                'patient': patient,
                'procedure_template': service_name,
                'docstatus': ['<', 2]
            }, limit=1)
        else:
            existing = []
    
        if existing:
            duplicates.append({
                'service_type': service_type,
                'service_name': service_name
            })
    
    return duplicates