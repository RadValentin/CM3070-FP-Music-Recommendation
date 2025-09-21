import "./LoadingSpinner.css";

type LoadingSpinnerProps = {
  theme?: "light" | "dark";
};

export default function LoadingSpinner({ theme = "dark" }: LoadingSpinnerProps) {
  return (
    <div className={`loading-spinner ${theme}`}>
      <span className="spinner"></span>
    </div>
  );
}