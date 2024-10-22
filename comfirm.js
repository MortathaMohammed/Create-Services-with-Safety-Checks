frappe.ui.form.on('Inpatient Record', {
    refresh: function(frm) {
        // Reset duplicate check flag when form is refreshed
        frm.is_duplicate_check_performed = false;
    },
    before_save: function(frm) {
        // Check if duplicate check has already been done
        if (frm.is_duplicate_check_performed) {
            return;
        }

        // Collect new services to check
        let services_to_check = [];

        function collect_services(child_table_field, service_type, service_name_field) {
            (frm.doc[child_table_field] || []).forEach(function(row) {
                // Check if custom_linked_document is not set
                if (!row.custom_linked_document || row.custom_linked_document === '') {
                    services_to_check.push({
                        service_type: service_type,
                        service_name: row[service_name_field],
                        row_name: row.name,
                        child_table_field: child_table_field
                    });
                }
            });
        }

        // Collect new entries from child tables
        collect_services('drug_prescription', 'Medication', 'drug_name');
        collect_services('lab_test_prescription', 'Lab Test', 'lab_test_code');
        collect_services('procedure_prescription', 'Procedure', 'procedure_name');

        if (services_to_check.length > 0) {
            frappe.validated = false;

            check_duplicates_and_proceed(frm, services_to_check);
        } else {
            frappe.validated = true;
        }
    },
    after_save: function(frm) {
        // Reload the form to get the latest data
        frm.reload_doc();
    }
});

function check_duplicates_and_proceed(frm, services_to_check) {
    frappe.call({
        method: 'custom_app.custom_app.inpatient_handler.check_duplicate_services',
        args: {
            patient: frm.doc.patient,
            services: services_to_check
        },
        callback: function(r) {
            if (r.message && r.message.length > 0) {
                let duplicates = r.message;
                let duplicate_list = duplicates.map(d => `${d.service_type}: ${d.service_name}`).join('<br>');
                frappe.confirm(
                    __('The following services already exist for this patient:<br>{0}<br>Do you want to create them again?', [duplicate_list]),
                    function() {
                        // User chose to proceed
                        frm.is_duplicate_check_performed = true;
                        frappe.validated = true;
                        frm.save();
                    },
                    function() {
                        // User chose to cancel
                        frappe.validated = false;
                    }
                );
            } else {
                // No duplicates found
                frm.is_duplicate_check_performed = true;
                frappe.validated = true;
                frm.save();
            }
        }
    });
}
