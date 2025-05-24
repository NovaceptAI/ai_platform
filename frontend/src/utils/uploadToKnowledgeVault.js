import axiosInstance from './axiosInstance';

const uploadToKnowledgeVault = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
        
            const response = await axiosInstance.post('/upload/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        });

        if (!response.data || !response.data.stored_as) {
            throw new Error('Invalid response from server');
        }

        return response.data.stored_as;
    } catch (error) {
        console.error('File upload failed:', error);
        throw new Error('File upload failed');
    }
};

export default uploadToKnowledgeVault;