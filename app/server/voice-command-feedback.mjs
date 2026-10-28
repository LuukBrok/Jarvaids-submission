const LABELS = {
  summary: "summary", visualisation: "visualisation", comparison: "comparison",
  voting: "voting list", suggestions: "suggestions", todo: "to-do list",
  requirements: "requirements or wishes list", planning: "agenda or schedule",
};

export function commandFeedback(heard, pollState = null, documentState = null, automatic = false, summaryAvailable = false) {
  if (!heard) return "Waiting for Hey Jarvaids and a command.";
  if (heard.status === "recognised" && heard.intent === "summary" && summaryAvailable)
    return "Summary update requested. Follow its progress in Overview.";
  if (automatic && heard.status === "recognised") {
    if (heard.intent === "voting" && pollState)
      return ({ draft:"Finding the poll question and choices…", open:"Voting is open.", closing:"Finishing earlier votes…", closed:"Voting finished.", cancelled:"Poll cancelled." })[pollState];
    if (["todo", "requirements", "planning"].includes(heard.intent) && documentState)
      return `${LABELS[heard.intent]} on canvas · ${documentState === "reviewing" ? "collection stopped" : documentState}.`;
  }
  if (heard.status === "recognised" && ["todo", "requirements", "planning"].includes(heard.intent) && documentState)
    return `Provisional command: ${LABELS[heard.intent]} ${heard.document_action || "creation"} requested. List on canvas: ${documentState}.`;
  if (heard.status === "recognised" && heard.poll_action)
    return `Provisional command: voting ${heard.poll_action} requested. ${pollState ? `Poll on canvas: ${pollState}.` : "No active poll."}`;
  if (heard.status === "recognised" && heard.intent === "voting" && pollState)
    return `Provisional command: voting list requested. Poll on canvas: ${pollState}.`;
  if (heard.status === "recognised" && Object.hasOwn(LABELS, heard.intent))
    return `Provisional command: ${LABELS[heard.intent]} requested. Generation is not connected yet.`;
  if (heard.status === "incomplete")
    return heard.command
      ? "Request unfinished. Continue straight away; two transcript lines can form one request."
      : "Hey Jarvaids recognised. Say your command straight away; two transcript lines can form one request.";
  return "Command not recognised. Try rephrasing: " + heard.command;
}
