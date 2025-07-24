
import { useState, useEffect } from "react";
import { useRouter } from "next/router";
import axios from "axios";
import toast, { Toaster } from "react-hot-toast";
import { Upload, Send, LogOut, FileText, MessageCircle, Plus, Trash2, Check, ArrowLeft, Bot, Download } from "lucide-react";

// Auto-detect API URL based on environment
const getApiUrl = () => {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  // If in production (Cloud Run), try to detect backend URL
  if (typeof window !== "undefined" && window.location.hostname.includes("run.app")) {
    return window.location.origin.replace("frontend", "backend");
  }
  // Fallback to localhost
  return "http://localhost:8080";
};

const API_URL = getApiUrl();

export default function Dashboard() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [token, setToken] = useState("");
  const [documents, setDocuments] = useState([]);
  const [selectedDocuments, setSelectedDocuments] = useState(new Set());
  const [loadingDocuments, setLoadingDocuments] = useState(false);
  const [currentAgent, setCurrentAgent] = useState(null);
  const [agentId, setAgentId] = useState(null);
  const [canGenerateCSV, setCanGenerateCSV] = useState(false);
  const [canGeneratePDF, setCanGeneratePDF] = useState(false);
  const [hasTable, setHasTable] = useState(false);
  const [generatingFile, setGeneratingFile] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const savedToken = localStorage.getItem("token");
    if (!savedToken) {
      router.push("/login");
    } else {
      setToken(savedToken);
      
      // Check if we have an agentId in URL
      const { agentId: urlAgentId } = router.query;
      if (urlAgentId) {
        setAgentId(urlAgentId);
        loadAgentData(urlAgentId, savedToken);
      } else {
        // No agent specified, redirect to agents page
        router.push("/agents");
      }
    }
  }, [router, router.query]);

  const loadAgentData = async (agentId, authToken) => {
    setLoadingDocuments(true);
    try {
      // Load agent info first
      const agentResponse = await axios.get(`${API_URL}/agents`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      
      const agent = agentResponse.data.agents?.find(a => a.id.toString() === agentId.toString());
      if (!agent) {
        toast.error("Agent non trouvé");
        router.push("/agents");
        return;
      }
      
      setCurrentAgent(agent);
      
      // Load documents for this specific agent
      const docsResponse = await axios.get(`${API_URL}/user/documents?agent_id=${agentId}`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      
      setDocuments(docsResponse.data.documents || []);
      // Select all agent's documents by default
      setSelectedDocuments(new Set((docsResponse.data.documents || []).map(doc => doc.id)));
      
    } catch (error) {
      console.error("Error loading agent data:", error);
      toast.error("Erreur lors du chargement de l'agent");
    } finally {
      setLoadingDocuments(false);
    }
  };

  const loadDocuments = async (authToken) => {
    setLoadingDocuments(true);
    try {
      const response = await axios.get(`${API_URL}/user/documents`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      setDocuments(response.data.documents);
      // Select all documents by default
      setSelectedDocuments(new Set(response.data.documents.map(doc => doc.id)));
    } catch (error) {
      console.error("Error loading documents:", error);
      toast.error("Erreur lors du chargement des documents");
    } finally {
      setLoadingDocuments(false);
    }
  };

  const askQuestion = async () => {
    if (!question.trim()) {
      toast.error("Veuillez poser une question");
      return;
    }
    setLoading(true);
    try {
      const response = await axios.post(
        `${API_URL}/ask`,
        { 
          question,
          selected_documents: Array.from(selectedDocuments),
          agent_type: currentAgent?.type || 'sales'
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
        }
      );
      
      setAnswer(response.data.answer);
      setCanGenerateCSV(response.data.can_generate_csv || false);
      setCanGeneratePDF(response.data.can_generate_pdf || false);
      setHasTable(response.data.has_table || false);
      
      toast.success("Réponse générée !");
    } catch (error) {
      console.error("Error:", error);
      toast.error("Erreur lors de la génération de la réponse");
    } finally {
      setLoading(false);
    }
  };

  const generateCSV = async () => {
    if (!canGenerateCSV) {
      toast.error("Aucun données structurées à exporter");
      return;
    }
    
    setGeneratingFile(true);
    try {
      const response = await axios.post(
        `${API_URL}/generate-csv`,
        { 
          question,
          selected_documents: Array.from(selectedDocuments),
          agent_type: currentAgent?.type || 'sales'
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          responseType: 'blob'
        }
      );
      
      // Créer et télécharger le fichier
      const blob = new Blob([response.data], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
      const agentType = currentAgent?.type || 'general';
      a.download = `rapport_${agentType}_${timestamp}.csv`;
      
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success("Fichier CSV généré et téléchargé !");
    } catch (error) {
      console.error("Error generating CSV:", error);
      toast.error("Erreur lors de la génération du CSV");
    } finally {
      setGeneratingFile(false);
    }
  };

  const generatePDF = async () => {
    if (!canGeneratePDF && !hasTable) {
      toast.error("Aucun contenu à exporter en PDF");
      return;
    }
    
    setGeneratingFile(true);
    try {
      const response = await axios.post(
        `${API_URL}/generate-pdf`,
        { 
          question,
          selected_documents: Array.from(selectedDocuments),
          agent_type: currentAgent?.type || 'sales'
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          responseType: 'blob'
        }
      );
      
      // Créer et télécharger le fichier
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      
      const timestamp = new Date().toISOString().slice(0, 19).replace(/[:-]/g, '');
      const agentType = currentAgent?.type || 'general';
      a.download = `rapport_${agentType}_${timestamp}.pdf`;
      
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
      toast.success("Fichier PDF généré et téléchargé !");
    } catch (error) {
      console.error("Error generating PDF:", error);
      toast.error("Erreur lors de la génération du PDF");
    } finally {
      setGeneratingFile(false);
    }
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    setUploadLoading(true);
    
    try {
      let response;
      
      if (currentAgent) {
        // Upload for specific agent
        const formData = new FormData();
        formData.append("file", file);
        formData.append("agent_id", currentAgent.id.toString());
        
        response = await axios.post(`${API_URL}/upload-agent`, formData, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        
        // Reload documents for current agent
        loadAgentData(currentAgent.id, token);
      } else {
        // Upload without agent (general upload)
        const formData = new FormData();
        formData.append("file", file);
        
        response = await axios.post(`${API_URL}/upload`, formData, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        
        // Reload all documents
        loadDocuments(token);
      }
      
      toast.success(`Document "${file.name}" ajouté avec succès !`);
      event.target.value = ""; // Reset file input
    } catch (error) {
      console.error("Upload error:", error);
      toast.error("Erreur lors de l'ajout du document");
    } finally {
      setUploadLoading(false);
    }
  };

  const deleteDocument = async (docId) => {
    try {
      await axios.delete(`${API_URL}/user/documents/${docId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocuments(prev => prev.filter(doc => doc.id !== docId));
      setSelectedDocuments(prev => {
        const newSet = new Set(prev);
        newSet.delete(docId);
        return newSet;
      });
      toast.success("Document supprimé");
    } catch (error) {
      console.error("Error deleting document:", error);
      toast.error("Erreur lors de la suppression");
    }
  };

  const toggleDocumentSelection = (docId) => {
    setSelectedDocuments(prev => {
      const newSet = new Set(prev);
      if (newSet.has(docId)) {
        newSet.delete(docId);
      } else {
        newSet.add(docId);
      }
      return newSet;
    });
  };

  const logout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <Toaster position="top-right" />
      {/* Left Sidebar - Sources */}
      <div className="w-80 bg-white shadow-lg border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center">
              <button
                onClick={() => router.push('/agents')}
                className="mr-3 p-1 text-gray-500 hover:text-blue-600 transition-colors"
                title="Retour aux agents"
              >
                <ArrowLeft className="w-5 h-5" />
              </button>
              <h2 className="text-xl font-bold text-gray-800 flex items-center">
                <FileText className="w-6 h-6 mr-2 text-blue-600" />
                Sources
              </h2>
            </div>
            <button
              onClick={logout}
              className="p-2 text-gray-500 hover:text-red-600 transition-colors"
              title="Se déconnecter"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
          
          {/* Agent Info */}
          {currentAgent && (
            <div className="mb-4 p-3 bg-gray-50 rounded-lg">
              <div className="flex items-center">
                <Bot className={`w-5 h-5 mr-2 ${
                  currentAgent.type === 'sales' ? 'text-green-600' :
                  currentAgent.type === 'marketing' ? 'text-purple-600' :
                  currentAgent.type === 'hr' ? 'text-blue-600' :
                  'text-orange-600'
                }`} />
                <div>
                  <p className="font-medium text-gray-800">{currentAgent.name} ({currentAgent.type})</p>
                  <p className="text-sm text-gray-600 capitalize">{currentAgent.type}</p>
                </div>
              </div>
            </div>
          )}
          
          {/* Add Document Button */}
          <label className="flex items-center justify-center w-full p-3 border-2 border-dashed border-blue-300 rounded-lg cursor-pointer hover:border-blue-400 hover:bg-blue-50 transition-colors">
            <input
              type="file"
              className="hidden"
              accept=".pdf,.txt,.docx"
              onChange={handleFileUpload}
              disabled={uploadLoading}
            />
            <Plus className="w-5 h-5 mr-2 text-blue-600" />
            <span className="text-blue-600 font-medium">
              {uploadLoading ? "Ajout en cours..." : "Ajouter"}
            </span>
          </label>
        </div>
        {/* Documents List */}
        <div className="flex-1 overflow-y-auto p-4">
          {loadingDocuments ? (
            <div className="text-center text-gray-500 py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
              Chargement des documents...
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <FileText className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p className="font-medium">Aucun document</p>
              <p className="text-sm">Ajoutez des documents pour commencer</p>
            </div>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className={`p-3 rounded-lg border transition-all ${
                    selectedDocuments.has(doc.id)
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 bg-gray-50 hover:bg-gray-100"
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    {/* Checkbox */}
                    <button
                      onClick={() => toggleDocumentSelection(doc.id)}
                      className={`flex-shrink-0 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors ${
                        selectedDocuments.has(doc.id)
                          ? "bg-blue-600 border-blue-600"
                          : "border-gray-300 hover:border-blue-400"
                      }`}
                    >
                      {selectedDocuments.has(doc.id) && (
                        <Check className="w-3 h-3 text-white" />
                      )}
                    </button>
                    {/* Document Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2">
                        <FileText className="w-4 h-4 text-gray-500 flex-shrink-0" />
                        <p className="text-sm font-medium text-gray-900 truncate" title={doc.filename}>
                          {doc.filename}
                        </p>
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        {new Date(doc.created_at).toLocaleDateString('fr-FR')}
                      </p>
                    </div>
                    {/* Delete Button */}
                    <button
                      onClick={() => deleteDocument(doc.id)}
                      className="flex-shrink-0 p-1 text-gray-400 hover:text-red-600 transition-colors"
                      title="Supprimer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col">
        {/* Chat Header */}
        <div className="border-b border-gray-200 p-4 bg-white">
          {currentAgent && (
            <div className="flex items-center">
              <Bot className={`w-6 h-6 mr-3 ${
                currentAgent.type === 'sales' ? 'text-green-600' :
                currentAgent.type === 'marketing' ? 'text-purple-600' :
                currentAgent.type === 'hr' ? 'text-blue-600' :
                'text-orange-600'
              }`} />
              <div>
                <h1 className="text-xl font-bold text-gray-800">{currentAgent.name} ({currentAgent.type})</h1>
                <p className="text-sm text-gray-600 capitalize">Agent {currentAgent.type}</p>
              </div>
            </div>
          )}
        </div>
        {/* Input Section */}
        <div className="border-b border-gray-200 p-6">
          <div className="flex space-x-4">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyPress={(e) => e.key === "Enter" && askQuestion()}
              placeholder="Posez votre question..."
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
            <button
              onClick={askQuestion}
              disabled={loading || !question.trim()}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
            >
              <Send className="w-4 h-4" />
              <span>{loading ? "..." : "Envoyer"}</span>
            </button>
          </div>
        </div>
        {/* Answer Area */}
        <div className="flex-1 p-6 bg-gray-50">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            </div>
          ) : answer ? (
            <div className="bg-white rounded-lg p-6 shadow-sm">
              <div className="prose max-w-none">
                <pre className="text-gray-800 leading-relaxed whitespace-pre-wrap font-sans text-sm overflow-x-auto">
                  {answer}
                </pre>
              </div>
              
              {/* File Generation Buttons */}
              {(canGenerateCSV || canGeneratePDF || hasTable) && (
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Exporter la réponse :</h4>
                  <div className="flex space-x-3">
                    {canGenerateCSV && (
                      <button
                        onClick={generateCSV}
                        disabled={generatingFile}
                        className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                      >
                        <Download className="w-4 h-4" />
                        <span>{generatingFile ? 'Génération...' : 'Télécharger CSV'}</span>
                      </button>
                    )}
                    
                    {(canGeneratePDF || hasTable) && (
                      <button
                        onClick={generatePDF}
                        disabled={generatingFile}
                        className="flex items-center space-x-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm"
                      >
                        <Download className="w-4 h-4" />
                        <span>{generatingFile ? 'Génération...' : 'Télécharger PDF'}</span>
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Welcome Message */
            <div className="text-center text-gray-500 py-12">
              <MessageCircle className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <h3 className="text-xl font-semibold mb-2">Bienvenue dans TAIC Companion</h3>
              <p className="mb-4">
                {documents.length === 0
                  ? "Ajoutez des documents et posez vos questions"
                  : "Posez une question basée sur vos documents sélectionnés"}
              </p>
              {documents.length > 0 && selectedDocuments.size > 0 && (
                <p className="text-sm text-blue-600">
                  {selectedDocuments.size} document{selectedDocuments.size > 1 ? 's' : ''} prêt{selectedDocuments.size > 1 ? 's' : ''} pour répondre à vos questions
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
