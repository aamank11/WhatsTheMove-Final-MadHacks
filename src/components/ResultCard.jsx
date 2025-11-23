// src/components/ResultCard.jsx

function ResultCard({ label, amount }) {
    return (
      <div className="result-card">
        <span className="result-label">{label}</span>
        <span className="result-amount">${amount.toLocaleString()}</span>
      </div>
    );
  }
  
  export default ResultCard;
  