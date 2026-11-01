const NEWS_PLUGIN = { id: "news", name: "News & Trends", description: "Pull current public news and topic trends from the site's discovery feed.", kind: "native", category: "Information" };
const CALCULATOR_PLUGIN = { id: "calculator", name: "Calculator", description: "Evaluate basic arithmetic locally on the site's backend.", kind: "native", category: "Utilities" };

// The directory mirrors the public ChatGPT plugin/app ecosystem at the time this
// file is generated. External services are catalogued here but require their own
// OAuth/API authorization; a ChatGPT connection cannot be silently transferred to
// a separate website.
const CONNECTORS = [
  ["gmail","Gmail","Find and reference emails from your inbox.","Productivity"],
  ["google-drive","Google Drive","Search and reference files from Drive, Docs, Sheets and Slides.","Files"],
  ["google-calendar","Google Calendar","Look up availability and manage calendar events.","Productivity"],
  ["outlook-email","Outlook Email","Search and reference Outlook email.","Productivity"],
  ["outlook-calendar","Outlook Calendar","Schedule and manage Outlook calendar events.","Productivity"],
  ["sharepoint","SharePoint","Search and reference shared sites and OneDrive content.","Files"],
  ["teams","Microsoft Teams","Look up chats and messages.","Communication"],
  ["slack","Slack","Search and work with Slack conversations.","Communication"],
  ["github","GitHub","Access repositories, issues, pull requests and CI workflows.","Developer Tools"],
  ["gitlab","GitLab","Work with repositories, issues and development workflows.","Developer Tools"],
  ["canva","Canva","Search, create and edit designs.","Design"],
  ["figma","Figma","Create, review and implement editable designs, slides and diagrams.","Design"],
  ["adobe","Adobe","Edit, combine, retouch and organize creative files.","Design"],
  ["product-design","Product Design","Turn product ideas into prototypes and research artifacts.","Design"],
  ["google-bigquery","BigQuery","Explore BigQuery data and generate SQL.","Data"],
  ["snowflake","Snowflake","Ask governed analytics questions of Snowflake data.","Data"],
  ["databricks","Databricks Genie","Analyze lakehouse data and dashboards.","Data"],
  ["clickhouse","ClickHouse","Explore ClickHouse Cloud data.","Data"],
  ["power-bi","Microsoft Power BI","Explore reports, visuals and dashboards.","Data"],
  ["salesforce","Salesforce","Review permitted CRM records and sales workflows.","Sales"],
  ["hubspot","HubSpot","Analyze and manage CRM records and pipeline workflows.","Sales"],
  ["stripe","Stripe","Analyze revenue, customers, subscriptions and payments.","Finance"],
  ["box","Box","Search, organize and reference documents.","Files"],
  ["dropbox","Dropbox","Access, save and share files.","Files"],
  ["notion","Notion","Search workspace knowledge and create or update pages.","Productivity"],
  ["linear","Linear","Search, create and update issues and projects.","Project Management"],
  ["atlassian","Atlassian","Work across Jira, Confluence, Bitbucket and other Atlassian tools.","Project Management"],
  ["zoom","Zoom","Use meeting context and Zoom workflows.","Communication"],
  ["calendly","Calendly","Create links and manage scheduling workflows.","Productivity"],
  ["todoist","Todoist","Manage tasks, projects, labels and reminders.","Productivity"],
  ["ticktick","TickTick","Manage tasks, calendars, reminders and habits.","Productivity"],
  ["superhuman","Superhuman Mail","Work across Gmail, Outlook and Google Calendar workflows.","Productivity"],
  ["icloud-mail","iCloud Mail","Read and manage iCloud mail.","Productivity"],
  ["icloud-calendar","iCloud Calendar","Read and manage iCloud calendars and events.","Productivity"],
  ["hostinger-mail","Hostinger Mail","Search, read, send and manage authenticated mailbox operations.","Productivity"],
  ["metricool","Metricool","Inspect social analytics and scheduled content.","Marketing"],
  ["klaviyo","Klaviyo","Analyze marketing campaign and flow performance.","Marketing"],
  ["windsor-ai","Windsor.ai","Connect marketing, analytics, CRM, social and commerce data.","Marketing"],
  ["zoominfo","ZoomInfo","Research companies, professionals and B2B signals.","Sales"],
  ["apollo","Apollo.io","Search and qualify accounts and contacts and support outbound workflows.","Sales"],
  ["attio","Attio","Manage CRM contacts, companies, deals, notes and tasks.","Sales"],
  ["close","Close","Work with calls, emails, SMS, meetings and sales records.","Sales"],
  ["clay","Clay","Find and engage prospects.","Sales"],
  ["rox","Rox","Analyze authenticated sales and account intelligence data.","Sales"],
  ["actively","Actively","Use account intelligence and next-best-action workflows.","Sales"],
  ["thoughtspot","ThoughtSpot SpotterCode","Build analytics workflows and AI-powered data experiences.","Data"],
  ["magicpath","MagicPath","Create interactive website and app prototypes.","Design"],
  ["tldraw","tldraw","Draw and diagram with an AI agent on a canvas.","Design"],
  ["vercel","Vercel","Build and deploy web applications and AI agents.","Developer Tools"],
  ["power-bi","Microsoft Power BI","Explore reports and build dashboard visuals.","Data"]
].map(([id,name,description,category]) => ({ id, name, description, category, kind: "connector", status: "connect-required" }));

const ALL_PLUGINS = [NEWS_PLUGIN, CALCULATOR_PLUGIN, ...CONNECTORS.filter((p, i, a) => a.findIndex(x => x.id === p.id) === i)];

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" } });
}

function tokenize(expression) {
  const tokens = []; let i = 0;
  while (i < expression.length) {
    const c = expression[i];
    if (/\s/.test(c)) { i++; continue; }
    if (/[0-9.]/.test(c)) { const start=i; let dots=0; while(i<expression.length&&/[0-9.]/.test(expression[i])){if(expression[i]===".")dots++;if(dots>1)throw Error("Invalid number.");i++;} const value=Number(expression.slice(start,i));if(!Number.isFinite(value))throw Error("Invalid number.");tokens.push({type:"number",value});continue; }
    if ("+-*/%()".includes(c)) { tokens.push({type:c}); i++; continue; }
    throw Error("Only numbers, parentheses and + - * / % are allowed.");
  } return tokens;
}
function calculate(expression) {
  if(typeof expression!=="string"||expression.length>300)throw Error("Enter a short arithmetic expression.");
  const tokens=tokenize(expression);if(!tokens.length)throw Error("Enter an expression.");
  const values=[],operators=[],precedence={"+":1,"-":1,"*":2,"/":2,"%":2};
  const apply=()=>{const op=operators.pop(),b=values.pop(),a=values.pop();if(a===undefined||b===undefined)throw Error("Invalid expression.");if(op==="+")values.push(a+b);else if(op==="-")values.push(a-b);else if(op==="*")values.push(a*b);else if(op==="/"){if(b===0)throw Error("Cannot divide by zero.");values.push(a/b);}else if(op==="%"){if(b===0)throw Error("Cannot divide by zero.");values.push(a%b);}};
  let expect=true;for(let i=0;i<tokens.length;i++){const t=tokens[i];if(t.type==="number"){if(!expect)throw Error("Invalid expression.");values.push(t.value);expect=false}else if(t.type==="("){if(!expect)throw Error("Invalid expression.");operators.push("(")}else if(t.type===")"){if(expect)throw Error("Invalid expression.");while(operators.length&&operators.at(-1)!=="(")apply();if(operators.pop()!=="(")throw Error("Unmatched parenthesis.")}else{if(expect){if(t.type==="-"&&(i===0||tokens[i-1].type==="("))values.push(0);else throw Error("Invalid expression.")}while(operators.length&&operators.at(-1)!=="("&&precedence[operators.at(-1)]>=precedence[t.type])apply();operators.push(t.type);expect=true}}
  if(expect)throw Error("Invalid expression.");while(operators.length){if(operators.at(-1)==="(")throw Error("Unmatched parenthesis.");apply()}if(values.length!==1||!Number.isFinite(values[0]))throw Error("Expression result is not finite.");return values[0];
}
async function runNews(request){const url=new URL(request.url);const response=await fetch(new URL("/api/social-feed",url),{headers:{Accept:"application/json"}});if(!response.ok)throw Error("The public news feed is temporarily unavailable.");const data=await response.json();return {plugin:NEWS_PLUGIN.id,title:NEWS_PLUGIN.name,items:Array.isArray(data.items)?data.items.slice(0,8):[]};}
export async function onRequestGet(){return json({ok:true,plugins:ALL_PLUGINS,active:ALL_PLUGINS.filter(p=>p.kind==="native").map(p=>p.id),connectorCount:ALL_PLUGINS.filter(p=>p.kind==="connector").length,source:"ChatGPT plugin/app ecosystem catalog; availability varies by plan, region, workspace and provider authorization."});}
export async function onRequestPost(context){try{const body=await context.request.json();const plugin=body?.plugin;if(plugin==="news")return json(await runNews(context.request));if(plugin==="calculator"){const result=calculate(body?.expression);return json({plugin:"calculator",title:CALCULATOR_PLUGIN.name,expression:body.expression,result});}const found=ALL_PLUGINS.find(p=>p.id===plugin);if(found&&found.kind==="connector")return json({plugin:found.id,title:found.name,connected:false,requiresAuthorization:true,message:`${found.name} is listed in the AI Hub, but it needs its own OAuth/API connection before the website can use it. Your ChatGPT account connection cannot be copied into this website.`});return json({error:"Unknown plugin."},400)}catch(error){return json({error:error instanceof Error?error.message:"Plugin request failed."},400)}}
