import React from "react";
import { Link } from "react-router-dom";
import { AlertTriangle } from "lucide-react";
import { Button } from "../components/common/Button";
import { Card } from "../components/common/Card";

export const NotFoundPage: React.FC = () => {
  return (
    <div className="max-w-md mx-auto text-center py-16">
      <Card className="space-y-4 p-8">
        <AlertTriangle className="w-12 h-12 text-highlight mx-auto" />
        <h2 className="text-2xl font-bold text-white">404 - Page Not Found</h2>
        <p className="text-sm text-slate-400">
          The pitch you're looking for doesn't exist or has been moved.
        </p>
        <Link to="/" className="inline-block pt-2">
          <Button variant="primary">Return Home</Button>
        </Link>
      </Card>
    </div>
  );
};

