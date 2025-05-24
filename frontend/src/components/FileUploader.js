import React, { useState } from 'react';
import uploadToKnowledgeVault from '../utils/uploadToKnowledgeVault';

const FileUploader = ({ onUploadComplete }) => {
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState('');

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploading(true);
        setError('');
        try {
            const filename = await uploadToKnowledgeVault(file);
            if (onUploadComplete) {
                onUploadComplete({ stored_as: filename });
            }
        } catch (err) {
            console.error('Upload failed:', err);
            setError('Upload failed. Please try again.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="space-y-2">
            <input type="file" onChange={handleFileChange} disabled={uploading} />
            {uploading && <p className="text-blue-600">Uploading...</p>}
            {error && <p className="text-red-600">{error}</p>}
        </div>
    );
};

export default FileUploader;