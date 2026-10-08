export default function Home() {
  return (
    <div style={{
      maxWidth: "640px",
      margin: "80px auto",
      padding: "0 24px",
      fontFamily: "var(--font-inter), system-ui, sans-serif",
      color: "#2B0B21",
      lineHeight: 1.55,
    }}>
      <h1 style={{
        fontSize: "32px",
        margin: "0 0 16px",
        fontWeight: 600,
        letterSpacing: "-0.01em",
      }}>
        Crew M Campaign Bot
      </h1>
      <p style={{ fontSize: "15.5px", color: "#4A2340", margin: "0 0 24px" }}>
        A Slack-triggered pipeline that drafts CleverTap campaigns for Plum
        clients. Most interaction happens in Slack. This page exists to confirm
        the service is live and signed in.
      </p>
      <p style={{ fontSize: "13px", color: "#6E5866", margin: 0 }}>
        See <code>CAMPAIGN-BOT-PLAN.md</code> in the repository for the build
        plan and how a campaign request flows end to end.
      </p>
    </div>
  );
}
