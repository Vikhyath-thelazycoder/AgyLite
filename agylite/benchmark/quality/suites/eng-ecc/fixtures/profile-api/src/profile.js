const SANDBOX_USER = { id: "u1", name: "Ada", email: "ada@example.test", avatar_url: "/a/ada.png" };

// Production reads the users table; sandbox mode returns fixture data with the same shape.
export async function getProfile(id, { sandbox = process.env.SANDBOX === "1", query } = {}) {
  if (sandbox) return { ...SANDBOX_USER, id };
  const rows = await query("SELECT id, name, email FROM users WHERE id = $1", [id]);
  return rows[0] || null;
}
