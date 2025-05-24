import React, { useState, useEffect } from 'react';
import axiosInstance from '../utils/axiosInstance';

const FileSelector = ({ onFileReady }) => {
    const [vaultFiles, setVaultFiles] = useState([]);
    const [selectedFile, setSelectedFile] = useState('');
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        fetchVaultFiles();
    }, []);

    const fetchVaultFiles = async () => {
        try {
            const response = await axiosInstance.get('/upload/files');
            setVaultFiles(response.data.files || []);
        } catch (err) {
            setError('Error fetching vault files.');
        }
    };

    const handleFileUpload = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploading(true);
        setError('');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await axiosInstance.post('/upload/upload/', formData);
            const storedAs = response.data.stored_as;
            await fetchVaultFiles();
            setSelectedFile(storedAs);
            onFileReady(storedAs);
        } catch (err) {
            console.error(err);
            setError('File upload failed.');
        } finally {
            setUploading(false);
        }
    };

    const handleVaultSelect = (e) => {
        const filename = e.target.value;
        setSelectedFile(filename);
        onFileReady(filename);
    };

    return (
        <div className="space-y-4">
            <div>
                <label className="block font-medium mb-1">Upload New File</label>
                <input type="file" onChange={handleFileUpload} disabled={uploading} />
            </div>

            <div>
                <label className="block font-medium mb-1">Or Select from Knowledge Vault</label>
                <select
                    className="w-full border p-2 rounded"
                    value={selectedFile}
                    onChange={handleVaultSelect}
                >
                    <option value="">-- Select a file --</option>
                    {vaultFiles.map((vf, idx) => (
                        <option key={idx} value={vf.name}>{vf.name}</option>
                    ))}
                </select>
            </div>

            {uploading && <p className="text-blue-600">Uploading file...</p>}
            {error && <p className="text-red-600">{error}</p>}
        </div>
    );
};

export default FileSelector;