frappe.ui.form.on('Inpatient Record', {
    refresh: function (frm) {
        console.log(frm.doc)
        // Call function to toggle child table read-only based on patient status
        toggle_service_tables_read_only(frm);
    },
    status: function (frm) {
        // Call function when status field is changed
        toggle_service_tables_read_only(frm);
    }
});

function toggle_service_tables_read_only(frm) {
    if (frm.doc.status !== "Admitted") {
        // Make the drug prescription, lab test prescription, and procedure prescription tables read-only
        frm.set_df_property('drug_prescription', 'read_only', 1);
        frm.set_df_property('lab_test_prescription', 'read_only', 1);
        frm.set_df_property('procedure_prescription', 'read_only', 1);

        // Show a message to the operator
        frappe.msgprint(__('You cannot add services as the patient is not admitted.'), 'Alert');
    } else {
        // If the patient is admitted, allow editing
        frm.set_df_property('drug_prescription', 'read_only', 0);
        frm.set_df_property('lab_test_prescription', 'read_only', 0);
        frm.set_df_property('procedure_prescription', 'read_only', 0);
    }
}
