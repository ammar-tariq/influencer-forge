import { Link, useNavigate } from "react-router-dom";

type Props = {
  /** Fallback when history has nothing useful to go back to */
  fallbackTo?: string;
  label?: string;
};

/** Consistent back control — prefers history, else a known parent route. */
export function BackLink({ fallbackTo = "/", label = "Back" }: Props) {
  const navigate = useNavigate();

  return (
    <button
      type="button"
      className="btn secondary"
      onClick={() => {
        if (window.history.length > 1) {
          navigate(-1);
        } else {
          navigate(fallbackTo);
        }
      }}
    >
      ← {label}
    </button>
  );
}

export function BackTo({ to, label }: { to: string; label: string }) {
  return (
    <Link className="btn secondary inline-block" to={to}>
      ← {label}
    </Link>
  );
}
