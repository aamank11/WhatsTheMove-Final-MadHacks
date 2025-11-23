// src/App.jsx
import { useState } from "react";
import "./App.css";

import LandingPage from "./pages/LandingPage.jsx";
import PlannerPage from "./pages/PlannerPage.jsx";
import ResultsPage from "./pages/ResultsPage.jsx";
import UploadPage from "./pages/Upload.jsx";

function App() {
  const [currentPage, setCurrentPage] = useState("landing");
  const [formData, setFormData] = useState({
    origin: "",
    destination: "",
    jobStartDate: "",
    jobEndDate: "",
    transportPlan: "",
    needsHousing: true,
    housingBudget: 1400,
    inUnitLaundry: false,
    // extras that Upload/Results can use:
    jobUrl: "",
    jobTitle: "",
    companyName: "",
    needsUhaul: undefined,
    wantsMovingServiceHelp: undefined,
  });

  const handleChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  return (
    <div className="app-root">
      {currentPage === "landing" && (
        <LandingPage
          onStart={() => setCurrentPage("planner")}
          onUpload={() => setCurrentPage("upload")}
          formData={formData}
          onChange={handleChange}
        />
      )}

      {currentPage === "upload" && (
        <UploadPage
          formData={formData}
          onChange={handleChange}
          onContinue={() => setCurrentPage("planner")}
        />
      )}

      {currentPage === "planner" && (
        <PlannerPage
          formData={formData}
          onChange={handleChange}
          onNext={() => setCurrentPage("results")}
        />
      )}

      {currentPage === "results" && (
        <ResultsPage
          formData={formData}
          onBack={() => setCurrentPage("planner")}
          onRestart={() => setCurrentPage("landing")}
        />
      )}
    </div>
  );
}

export default App;
