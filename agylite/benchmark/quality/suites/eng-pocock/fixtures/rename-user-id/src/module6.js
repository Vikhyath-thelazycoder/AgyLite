export function invoiceFor6(db, user_id) {
  return db.query('select * from invoices where user_id = $1', [user_id]);
}
export const field6 = (invoice) => invoice.user_id;
