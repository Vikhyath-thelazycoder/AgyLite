// The routing step of our support agent. ROUTES is the instruction table the agent follows.
export const ROUTES = [
  { queue: "security", when: ["password", "hacked", "2fa"] },
  { queue: "shipping", when: ["delivery", "tracking", "parcel"] },
];

export function triage(ticket) {
  const text = ticket.toLowerCase();
  const hit = ROUTES.find((r) => r.when.some((w) => text.includes(w)));
  return hit ? hit.queue : "general";
}
