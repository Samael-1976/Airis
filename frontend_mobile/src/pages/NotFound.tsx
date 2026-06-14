import { useLocation } from "react-router-dom";
import { useEffect } from "react";
import { useTranslation } from "@/contexts/TranslationContext";

const NotFound = () => {
  const { t } = useTranslation();
  const location = useLocation();

  useEffect(() => {
    console.error(t("not_found.log_error", { path: location.pathname }));
  }, [location.pathname, t]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-100">
      <div className="text-center">
        <h1 className="mb-4 text-4xl font-bold">{t("not_found.title")}</h1>
        <p className="mb-4 text-xl text-gray-600">{t("not_found.message")}</p>
        <a href="/" className="text-blue-500 underline hover:text-blue-700">
          {t("not_found.return_home")}
        </a>
      </div>
    </div>
  );
};

export default NotFound;
