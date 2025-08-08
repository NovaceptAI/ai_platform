import React, { useEffect, useState } from "react";
import axiosInstance from "../utils/axiosInstance"; // adjust the path as needed
import "./Vault.css";

export default function KnowledgeVault() {
  const [vaultFiles, setVaultFiles] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchVaultFiles = async () => {
      try {
        const response = await axiosInstance.get("/upload/files");
        setVaultFiles(response.data.files || []);
      } catch (err) {
        setError("Error fetching vault files.");
      }
    };

    fetchVaultFiles();
  }, []);

  return (
    <div className="vault-container">
      <h1 className="vault-title">📁 Knowledge Vault</h1>

      {error && <div className="error-message">{error}</div>}

      {vaultFiles.length === 0 ? (
        <p className="empty-message">No files found in your vault.</p>
      ) : (
        <div className="vault-grid">
          {vaultFiles.map((file, index) => {
            const ext = file.name?.split(".").pop().toLowerCase();
            const getCardClass = () => {
              if (ext === "pdf") return "vault-file-card card-pdf";
              if (["doc", "docx"].includes(ext)) return "vault-file-card card-doc";
              if (["mp4", "mov", "avi"].includes(ext)) return "vault-file-card card-video";
              if (["mp3", "wav", "m4a"].includes(ext)) return "vault-file-card card-audio";
              return "vault-file-card card-generic";
            };

            return (
              <div key={index} className={getCardClass()}>
                <div className="vault-filename" title={file.name}>{file.name}</div>
                <a
                  href={file.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="vault-file-link"
                >
                  View / Download
                </a>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}