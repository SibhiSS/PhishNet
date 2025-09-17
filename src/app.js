import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  ShieldAlert,
  ShieldCheck,
  Mail,
  Link2,
  FileText,
  AlertTriangle,
  CheckCircle,
  Loader2,
} from "lucide-react";

export default function App() {
  const [email, setEmail] = useState({
    sender: "Eswar <vellingrieshwar@gmail.com>",
    subject: "DQ2",
    body: "Wow, your work has been amazing lately! Could you send me the details of your last project?",
    spam: "HAM ✅",
    social: {
      modelProb: 0.64,
      ruleScore: 0.0,
      combinedProb: 0.45,
      threshold: 0.45,
      label: "Attack 🎭",
      triggers: ["Flattery + request for sensitive info"],
    },
    urls: [
      { url: "https://safe-link.com", verdict: "Safe ✅" },
      { url: "https://phishy-link.biz", verdict: "Malicious ❌" },
    ],
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-6">
      <motion.h1
        className="text-4xl font-bold mb-6 text-center"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        📩 PhishNet Dashboard
      </motion.h1>

      {/* Email card */}
      <motion.div
        className="bg-slate-800 rounded-2xl shadow-xl p-6 mb-6"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
      >
        <h2 className="text-xl font-semibold flex items-center gap-2 mb-2">
          <Mail className="w-5 h-5 text-blue-400" /> Latest Email
        </h2>
        <p>
          <span className="font-bold">From:</span> {email.sender}
        </p>
        <p>
          <span className="font-bold">Subject:</span> {email.subject}
        </p>
        <div className="mt-4 bg-slate-900 p-4 rounded-xl">
          <FileText className="inline w-4 h-4 text-gray-400 mr-2" />
          {email.body}
        </div>
      </motion.div>

      {/* Spam classification */}
      <motion.div
        className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6"
        initial="hidden"
        animate="visible"
        variants={{
          hidden: {},
          visible: { transition: { staggerChildren: 0.2 } },
        }}
      >
        <motion.div
          className="bg-slate-800 rounded-2xl p-6 shadow-lg"
          variants={{ hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0 } }}
        >
          <h3 className="text-lg font-semibold mb-4">Spam Detection</h3>
          {email.spam.startsWith("HAM") ? (
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-green-500/20 text-green-400">
              <ShieldCheck className="w-4 h-4 mr-1" /> {email.spam}
            </span>
          ) : (
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-red-500/20 text-red-400">
              <ShieldAlert className="w-4 h-4 mr-1" /> {email.spam}
            </span>
          )}
        </motion.div>

        {/* Social Engineering */}
        <motion.div
          className="bg-slate-800 rounded-2xl p-6 shadow-lg"
          variants={{ hidden: { opacity: 0, y: 30 }, visible: { opacity: 1, y: 0 } }}
        >
          <h3 className="text-lg font-semibold mb-4">Social Engineering</h3>
          <div className="mb-2">Model Prob: {email.social.modelProb.toFixed(2)}</div>
          <div className="mb-2">Rule Score: {email.social.ruleScore.toFixed(2)}</div>
          <div className="mb-2">
            Combined: {email.social.combinedProb.toFixed(2)} (thr {email.social.threshold})
          </div>
          {email.social.label.includes("Attack") ? (
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-red-500/20 text-red-400">
              <AlertTriangle className="w-4 h-4 mr-1" /> {email.social.label}
            </span>
          ) : (
            <span className="inline-flex items-center px-3 py-1 rounded-full bg-green-500/20 text-green-400">
              <CheckCircle className="w-4 h-4 mr-1" /> {email.social.label}
            </span>
          )}
          {email.social.triggers.length > 0 && (
            <div className="mt-3 text-sm text-gray-300">
              <strong>Triggers:</strong>
              <ul className="list-disc ml-5">
                {email.social.triggers.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          )}
        </motion.div>
      </motion.div>

      {/* URLs */}
      <motion.div
        className="bg-slate-800 rounded-2xl p-6 shadow-xl"
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Link2 className="w-5 h-5 text-indigo-400" /> URL Analysis
        </h3>
        <ul className="space-y-2">
          {email.urls.map((u, i) => (
            <motion.li
              key={i}
              className="bg-slate-900 p-3 rounded-xl flex justify-between items-center"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.2 + i * 0.1 }}
            >
              <span className="truncate">{u.url}</span>
              <span
                className={`px-2 py-1 rounded-md text-sm ${
                  u.verdict.includes("Safe")
                    ? "bg-green-500/20 text-green-400"
                    : u.verdict.includes("Malicious")
                    ? "bg-red-500/20 text-red-400"
                    : "bg-yellow-500/20 text-yellow-400"
                }`}
              >
                {u.verdict}
              </span>
            </motion.li>
          ))}
        </ul>
      </motion.div>
    </div>
  );
}
