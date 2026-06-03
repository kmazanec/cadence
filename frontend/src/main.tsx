import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles/index.css";
import ChatApp from "./chat/ChatApp";

const root = document.getElementById("root");
if (!root) throw new Error("No #root element found");

createRoot(root).render(
  <StrictMode>
    <ChatApp />
  </StrictMode>,
);
