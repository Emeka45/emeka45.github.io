const TOOLS = [
  {
    id: "web-search",
    name: "Web Search",
    description: "Search the public web for current information and ground answers with Google Search.",
    status: "active",
    provider: "Gemini"
  },
  {
    id: "code-execution",
    name: "Code Execution",
    description: "Run Python calculations and data-processing code when a problem benefits from computation.",
    status: "active",
    provider: "Gemini"
  },
  {
    id: "url-context",
    name: "URL Context",
    description: "Read and analyze a user-supplied web page or document URL.",
    status: "ready-next",
    provider: "Gemini"
  },
  {
    id: "github",
    name: "GitHub",
    description: "Repository, issue and code workflows through an authenticated connector.",
    status: "connector-slot",
    provider: "External connector"
  },
  {
    id: "canva",
    name: "Canva",
    description: "Create, inspect and work with Canva designs through an authenticated connector.",
    status: "connector-slot",
    provider: "External connector"
  },
  {
    id: "cloud-storage",
    name: "Cloud Storage",
    description: "Future connector family for Drive, OneDrive and Dropbox files.",
    status: "connector-slot",
    provider: "External connector"
  },
  {
    id: "email-calendar",
    name: "Email & Calendar",
    description: "Future authenticated connectors for Gmail, Outlook and calendars.",
    status: "connector-slot",
    provider: "External connector"
  }
];

export function onRequestGet() {
  return Response.json({
    ok: true,
    service: "C. O. Eric Universal AI",
    tools: TOOLS,
    note: "External connectors require their own OAuth/API credentials; ChatGPT-installed apps are not automatically transferred to a website backend."
  });
}
