const NEWS_PLUGIN = {
  id: "news",
  name: "News & Trends",
  description: "Pull current public news and topic trends from the site's discovery feed."
};

const CALCULATOR_PLUGIN = {
  id: "calculator",
  name: "Calculator",
  description: "Evaluate basic arithmetic without sending the expression to an AI provider."
};

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff"
    }
  });
}

function tokenize(expression) {
  const tokens = [];
  let i = 0;
  while (i < expression.length) {
    const c = expression[i];
    if (/\s/.test(c)) { i += 1; continue; }
    if (/[0-9.]/.test(c)) {
      const start = i;
      let dots = 0;
      while (i < expression.length && /[0-9.]/.test(expression[i])) {
        if (expression[i] === ".") dots += 1;
        if (dots > 1) throw new Error("Invalid number.");
        i += 1;
      }
      const value = Number(expression.slice(start, i));
      if (!Number.isFinite(value)) throw new Error("Invalid number.");
      tokens.push({ type: "number", value });
      continue;
    }
    if ("+-*/%()".includes(c)) { tokens.push({ type: c }); i += 1; continue; }
    throw new Error("Only numbers, parentheses and + - * / % are allowed.");
  }
  return tokens;
}

function calculate(expression) {
  if (typeof expression !== "string" || expression.length > 300) throw new Error("Enter a short arithmetic expression.");
  const tokens = tokenize(expression);
  if (!tokens.length) throw new Error("Enter an expression.");
  const values = [];
  const operators = [];
  const precedence = { "+": 1, "-": 1, "*": 2, "/": 2, "%": 2 };

  const apply = () => {
    const op = operators.pop();
    const b = values.pop();
    const a = values.pop();
    if (a === undefined || b === undefined) throw new Error("Invalid expression.");
    if (op === "+") values.push(a + b);
    else if (op === "-") values.push(a - b);
    else if (op === "*") values.push(a * b);
    else if (op === "/") {
      if (b === 0) throw new Error("Cannot divide by zero.");
      values.push(a / b);
    } else if (op === "%") {
      if (b === 0) throw new Error("Cannot divide by zero.");
      values.push(a % b);
    }
  };

  let expectValue = true;
  for (let i = 0; i < tokens.length; i += 1) {
    const token = tokens[i];
    if (token.type === "number") {
      if (!expectValue) throw new Error("Invalid expression.");
      values.push(token.value);
      expectValue = false;
    } else if (token.type === "(") {
      if (!expectValue) throw new Error("Invalid expression.");
      operators.push("(");
    } else if (token.type === ")") {
      if (expectValue) throw new Error("Invalid expression.");
      while (operators.length && operators[operators.length - 1] !== "(") apply();
      if (operators.pop() !== "(") throw new Error("Unmatched parenthesis.");
    } else {
      if (expectValue) {
        if (token.type === "-" && (i === 0 || tokens[i - 1].type === "(")) values.push(0);
        else throw new Error("Invalid expression.");
      }
      while (operators.length && operators[operators.length - 1] !== "(" && precedence[operators[operators.length - 1]] >= precedence[token.type]) apply();
      operators.push(token.type);
      expectValue = true;
    }
  }
  if (expectValue) throw new Error("Invalid expression.");
  while (operators.length) {
    if (operators[operators.length - 1] === "(") throw new Error("Unmatched parenthesis.");
    apply();
  }
  if (values.length !== 1 || !Number.isFinite(values[0])) throw new Error("Expression result is not finite.");
  return values[0];
}

async function runNews(request) {
  const url = new URL(request.url);
  const response = await fetch(new URL("/api/social-feed", url), { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error("The public news feed is temporarily unavailable.");
  const data = await response.json();
  const items = Array.isArray(data.items) ? data.items.slice(0, 8) : [];
  return { plugin: NEWS_PLUGIN.id, title: NEWS_PLUGIN.name, items };
}

export async function onRequestGet() {
  return json({ plugins: [NEWS_PLUGIN, CALCULATOR_PLUGIN] });
}

export async function onRequestPost(context) {
  try {
    const body = await context.request.json();
    const plugin = body?.plugin;
    if (plugin === "news") return json(await runNews(context.request));
    if (plugin === "calculator") {
      const result = calculate(body?.expression);
      return json({ plugin: "calculator", title: CALCULATOR_PLUGIN.name, expression: body.expression, result });
    }
    return json({ error: "Unknown plugin." }, 400);
  } catch (error) {
    return json({ error: error instanceof Error ? error.message : "Plugin request failed." }, 400);
  }
}
