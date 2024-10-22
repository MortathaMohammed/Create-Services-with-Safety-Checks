frappe.ui.form.on('Inpatient Record', {
    refresh: function (frm) {
        console.log(frm.doc)
        toggle_service_tables_read_only(frm);
    },
    status: function (frm) {
        toggle_service_tables_read_only(frm);
    }
});

function toggle_service_tables_read_only(frm) {
    if (frm.doc.status !== "Admitted") {
        frm.set_df_property('drug_prescription', 'read_only', 1);
        frm.set_df_property('lab_test_prescription', 'read_only', 1);
        frm.set_df_property('procedure_prescription', 'read_only', 1);

        frappe.msgprint(__('You cannot add services as the patient is not admitted.'), 'Alert');
    } else {
        frm.set_df_property('drug_prescription', 'read_only', 0);
        frm.set_df_property('lab_test_prescription', 'read_only', 0);
        frm.set_df_property('procedure_prescription', 'read_only', 0);
    }
}
