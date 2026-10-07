"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Megaphone, Loader2, ExternalLink, Copy, Check } from "lucide-react";

type CampaignType = "welcome" | "renewal";

interface DraftResult {
  id?: string;
  campaignName: string;
  channel: string;
  subject: string;
  body: string;
  creativeUrl: string;
  creativeIsStub: boolean;
  segmentSuggestion: string;
  reviewUrl: string;
}

function NewCampaignForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [amName, setAmName] = useState("");
  const [accountName, setAccountName] = useState("");
  const [campaignType, setCampaignType] = useState<CampaignType>("welcome");
  const [logoUrl, setLogoUrl] = useState("");

  const [status, setStatus] = useState<"idle" | "loading" | "error" | "done">("idle");
  const [errorMessage, setErrorMessage] = useState("");
  const [result, setResult] = useState<DraftResult | null>(null);
  const [copied, setCopied] = useState(false);

  // Load a shared result straight from its saved record, e.g. /new-campaign?id=...
  useEffect(() => {
    const id = searchParams.get("id");
    if (!id) return;
    setStatus("loading");
    fetch(`/api/campaign/${id}`)
      .then((res) => {
        if (!res.ok) throw new Error("That campaign link couldn't be found.");
        return res.json();
      })
      .then((draft: DraftResult) => {
        setResult(draft);
        setStatus("done");
      })
      .catch((err) => {
        setErrorMessage(err instanceof Error ? err.message : "Something went wrong.");
        setStatus("error");
      });
  }, [searchParams]);

  const canSubmit = amName.trim().length > 0 && accountName.trim().length > 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit || status === "loading") return;

    setStatus("loading");
    setErrorMessage("");
    setResult(null);

    const requestId = `web-${Date.now()}`;

    try {
      const copyRes = await fetch("/api/copy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requestId, amName, accountName, campaignType, logoUrl }),
      });
      if (!copyRes.ok) throw new Error("Couldn't generate copy. Try again.");
      const copy = await copyRes.json();

      const creativeRes = await fetch("/api/creative", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requestId, copy, logoUrl: logoUrl.trim() || undefined }),
      });
      if (!creativeRes.ok) throw new Error("Couldn't render the creative. Try again.");
      const creative = await creativeRes.json();

      const draftRes = await fetch("/api/campaign/draft", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ requestId, amName, accountName, campaignType, copy, creative }),
      });
      if (!draftRes.ok) throw new Error("Couldn't assemble the campaign brief. Try again.");
      const draft: DraftResult = await draftRes.json();

      setResult(draft);
      setStatus("done");
      if (draft.id) {
        router.replace(`/new-campaign?id=${draft.id}`, { scroll: false });
      }
    } catch (err) {
      setErrorMessage(err instanceof Error ? err.message : "Something went wrong. Try again.");
      setStatus("error");
    }
  }

  function handleReset() {
    setStatus("idle");
    setResult(null);
    setErrorMessage("");
    router.replace("/new-campaign", { scroll: false });
  }

  async function handleCopyLink() {
    await navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  const [copiedField, setCopiedField] = useState<string | null>(null);
  async function handleCopyField(field: string, value: string) {
    await navigator.clipboard.writeText(value);
    setCopiedField(field);
    setTimeout(() => setCopiedField((f) => (f === field ? null : f)), 2000);
  }

  function FieldCopyButton({ field, value }: { field: string; value: string }) {
    return (
      <Button variant="ghost" size="xs" onClick={() => handleCopyField(field, value)}>
        {copiedField === field ? (
          <>
            <Check className="w-3 h-3" />
            Copied
          </>
        ) : (
          <>
            <Copy className="w-3 h-3" />
            Copy
          </>
        )}
      </Button>
    );
  }

  const isLoadingSharedLink = status === "loading" && Boolean(searchParams.get("id")) && !result;

  return (
    <div className="py-6 space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">New campaign</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Fill in the account and campaign type — copy and a creative brief get drafted for you.
        </p>
      </div>

      {isLoadingSharedLink && (
        <Card>
          <CardContent className="py-8 flex items-center justify-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-4 h-4 animate-spin" />
            Loading campaign…
          </CardContent>
        </Card>
      )}

      {status !== "done" && !isLoadingSharedLink && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center gap-2">
              <Megaphone className="w-4 h-4 text-muted-foreground" />
              <CardTitle className="text-sm font-medium">Campaign request</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={handleSubmit}>
              <div className="space-y-1.5">
                <label htmlFor="am-name" className="text-sm font-medium">
                  Your name
                </label>
                <input
                  id="am-name"
                  type="text"
                  value={amName}
                  onChange={(e) => setAmName(e.target.value)}
                  placeholder="Jordan Lee"
                  className="w-full h-9 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:border-ring"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <label htmlFor="account-name" className="text-sm font-medium">
                  Account name
                </label>
                <input
                  id="account-name"
                  type="text"
                  value={accountName}
                  onChange={(e) => setAccountName(e.target.value)}
                  placeholder="Acme Corp"
                  className="w-full h-9 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:border-ring"
                  required
                />
              </div>

              <div className="space-y-1.5">
                <span className="text-sm font-medium">Campaign type</span>
                <div className="flex gap-2" role="radiogroup" aria-label="Campaign type">
                  {(["welcome", "renewal"] as const).map((type) => (
                    <Button
                      key={type}
                      type="button"
                      role="radio"
                      aria-checked={campaignType === type}
                      variant={campaignType === type ? "default" : "outline"}
                      size="lg"
                      className="capitalize flex-1"
                      onClick={() => setCampaignType(type)}
                    >
                      {type}
                    </Button>
                  ))}
                </div>
              </div>

              <div className="space-y-1.5">
                <label htmlFor="logo-url" className="text-sm font-medium">
                  Client logo URL <span className="text-muted-foreground font-normal">(optional)</span>
                </label>
                <input
                  id="logo-url"
                  type="url"
                  value={logoUrl}
                  onChange={(e) => setLogoUrl(e.target.value)}
                  placeholder="https://..."
                  className="w-full h-9 rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:border-ring"
                />
              </div>

              {status === "error" && (
                <p className="text-sm text-destructive">{errorMessage}</p>
              )}

              <Button type="submit" size="lg" className="w-full" disabled={!canSubmit || status === "loading"}>
                {status === "loading" ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Drafting… this can take up to 30 seconds
                  </>
                ) : (
                  "Draft campaign"
                )}
              </Button>
            </form>
          </CardContent>
        </Card>
      )}

      {status === "done" && result && (
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-medium">{result.campaignName}</CardTitle>
              <div className="flex items-center gap-1">
                <Button variant="ghost" size="sm" onClick={handleCopyLink}>
                  {copied ? (
                    <>
                      <Check className="w-3.5 h-3.5" />
                      Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      Copy link
                    </>
                  )}
                </Button>
                <Button variant="ghost" size="sm" onClick={handleReset}>
                  New request
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-muted-foreground">
              {result.channel} campaign — this is a brief, not a live CleverTap draft.
              CleverTap doesn&apos;t expose an API to create campaigns, so someone with
              Creator access pastes this in to build the real draft.
            </p>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Campaign name
                </span>
                <FieldCopyButton field="name" value={result.campaignName} />
              </div>
              <p className="text-sm font-mono bg-muted rounded-lg px-3 py-2">
                {result.campaignName}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Subject
                </span>
                <FieldCopyButton field="subject" value={result.subject} />
              </div>
              <p className="text-sm font-medium bg-muted rounded-lg px-3 py-2">
                {result.subject}
              </p>
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Body
                </span>
                <FieldCopyButton field="body" value={result.body} />
              </div>
              <p className="text-sm whitespace-pre-wrap bg-muted rounded-lg p-4">
                {result.body}
              </p>
            </div>

            <div className="space-y-1">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Creative
              </span>
              {result.creativeUrl && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={result.creativeUrl}
                  alt="Campaign creative"
                  className="w-full rounded-lg border border-border"
                />
              )}
              {result.creativeIsStub && (
                <p className="text-xs text-muted-foreground">
                  Placeholder — real creative rendering isn&apos;t wired up yet.
                </p>
              )}
            </div>

            <div className="space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Suggested audience
                </span>
                <FieldCopyButton field="audience" value={result.segmentSuggestion} />
              </div>
              <p className="text-sm bg-muted rounded-lg px-3 py-2">{result.segmentSuggestion}</p>
            </div>

            <Separator />

            <div className="space-y-2">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                To create the real draft in CleverTap
              </span>
              <ol className="text-sm space-y-1 list-decimal list-inside text-foreground">
                <li>
                  Open CleverTap and start a new campaign under{" "}
                  <strong>Campaigns → {result.channel}</strong>.
                </li>
                <li>
                  <strong>Start Here:</strong> paste the campaign name above.
                </li>
                <li>
                  <strong>Who:</strong> build the segment described above.
                </li>
                <li>
                  <strong>What:</strong> paste the subject and body above into the editor.
                </li>
                <li>
                  <strong>When / Publish:</strong> leave it as a draft — do not schedule
                  or publish. A PMM reviews and publishes it from here.
                </li>
              </ol>
              <a
                href={result.reviewUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
              >
                Open CleverTap
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

export default function NewCampaignPage() {
  return (
    <Suspense>
      <NewCampaignForm />
    </Suspense>
  );
}
