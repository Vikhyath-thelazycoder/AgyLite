export function invoiceFor5(db, user_id) {
  return db.query('select * from invoices where user_id = $1', [user_id]);
}
export const field5 = (invoice) => invoice.user_id;
