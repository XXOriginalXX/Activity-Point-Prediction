import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Upload, FileText, Award, AlertTriangle } from 'lucide-react';
import { toast } from 'react-hot-toast';

interface ActivityPointsPredictionProps {
  username: string;
}

const ActivityPointsPrediction: React.FC<ActivityPointsPredictionProps> = ({ username }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [predictedPoints, setPredictedPoints] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file size (e.g., max 16MB)
      if (file.size > 16 * 1024 * 1024) {
        toast.error('File size exceeds 16MB limit');
        return;
      }

      // Validate file type
      const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
      if (!allowedTypes.includes(file.type)) {
        toast.error('Invalid file type. Please upload JPG, PNG, or PDF');
        return;
      }

      setSelectedFile(file);
      setPredictedPoints(null);
      setError(null);
    }
  };

  const convertToBase64 = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = (error) => reject(error);
    });
  };

  const handleFileUpload = async () => {
    if (!selectedFile) {
      toast.error('Please select a file first');
      return;
    }

    setIsLoading(true);
    setError(null);
    setPredictedPoints(null);

    try {
      // Convert file to base64
      const base64File = await convertToBase64(selectedFile);

      // Prepare payload
      const payload = {
        username,
        certificate: base64File,
        filename: selectedFile.name
      };

      // Simulated API call for OCR and ML points prediction
      const response = await axios.post('https://activity-point-prediction.onrender.com/predict-points', payload, {
        headers: {
          'Content-Type': 'application/json'
        },
        timeout: 30000 // 30 seconds timeout
      });

      // Process response
      const { points, certificateType } = response.data;

      setPredictedPoints(points);
      
      // Notify user about points
      toast.success(`${certificateType} Processed! ${points} points awarded.`);
    } catch (err) {
      console.error('Points prediction error:', err);
      
      // Detailed error handling
      if (axios.isAxiosError(err)) {
        if (err.response) {
          // The request was made and the server responded with a status code
          // that falls out of the range of 2xx
          const errorMessage = err.response.data?.error || 'Server error occurred';
          setError(errorMessage);
          toast.error(errorMessage);
        } else if (err.request) {
          // The request was made but no response was received
          setError('No response from server. Please check your internet connection.');
          toast.error('Network error. Please check your connection.');
        } else {
          // Something happened in setting up the request that triggered an Error
          setError('An unexpected error occurred. Please try again.');
          toast.error('Unexpected error. Please try again.');
        }
      } else {
        // Fallback for non-axios errors
        setError('Failed to process certificate. Please try again.');
        toast.error('Certificate processing failed');
      }
    } finally {
      setIsLoading(false);
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  return (
    <div className="bg-gray-900 rounded-lg p-6 space-y-4">
      <h2 className="text-2xl font-bold mb-4 flex items-center">
        <Award className="mr-3 text-yellow-500" />
        Activity Points Prediction
      </h2>

      <div className="border-2 border-dashed border-gray-700 rounded-lg p-6 text-center">
        <input 
          type="file" 
          ref={fileInputRef}
          onChange={handleFileChange}
          accept=".pdf,.jpg,.jpeg,.png"
          className="hidden"
          id="certificate-upload"
        />
        <label 
          htmlFor="certificate-upload" 
          className="cursor-pointer flex flex-col items-center"
        >
          <Upload size={48} className="text-blue-400 mb-4" />
          <p className="text-gray-400">
            {selectedFile 
              ? `Selected: ${selectedFile.name}` 
              : 'Upload Certificate (PDF, JPG, PNG)'}
          </p>
        </label>
      </div>

      {selectedFile && (
        <button 
          onClick={handleFileUpload}
          disabled={isLoading}
          className="w-full bg-blue-600 text-white py-3 rounded-lg hover:bg-blue-700 transition-colors"
        >
          {isLoading ? 'Processing...' : 'Predict Points'}
        </button>
      )}

      {isLoading && (
        <div className="flex justify-center items-center">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-blue-500"></div>
        </div>
      )}

      {predictedPoints !== null && !isLoading && (
        <div className="bg-gray-800 rounded-lg p-4 flex items-center justify-between">
          <div className="flex items-center">
            <FileText className="text-green-400 mr-3" />
            <div>
              <p className="font-semibold">Points Awarded</p>
              <p className="text-gray-400">Based on certificate analysis</p>
            </div>
          </div>
          <div className="text-2xl font-bold text-yellow-500">
            {predictedPoints} Points
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-900/20 border border-red-500 rounded-lg p-4 flex items-center">
          <AlertTriangle className="text-red-500 mr-3" />
          <p className="text-red-400">{error}</p>
        </div>
      )}

      <div className="text-sm text-gray-500 mt-4">
        <p>How Points are Calculated:</p>
        <ul className="list-disc list-inside">
          <li>NPTEL Certificates: 50 points</li>
          <li>Hackathon/Competition Certificates: 40 points</li>
          <li>Internship Certificates: 30 points</li>
          <li>Professional Development Certificates: 20 points</li>
          <li>Other Certificates: 10 points</li>
        </ul>
      </div>
    </div>
  );
};

export default ActivityPointsPrediction;
