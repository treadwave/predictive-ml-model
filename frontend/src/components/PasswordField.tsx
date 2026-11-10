import { type InputHTMLAttributes, useId, useState } from "react";

type PasswordFieldProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "id"> & {
  label: string;
};

export function PasswordField({ label, ...inputProps }: PasswordFieldProps) {
  const id = useId();
  const [visible, setVisible] = useState(false);

  return <div className="password-field">
    <label htmlFor={id}>{label}</label>
    <div className="password-control">
      <input {...inputProps} id={id} type={visible ? "text" : "password"} />
      <button type="button" className="password-toggle" disabled={inputProps.disabled}
        aria-label={`${visible ? "Скрыть" : "Показать"}: ${label.toLowerCase()}`}
        aria-controls={id} aria-pressed={visible} onClick={() => setVisible(value => !value)}>
        {visible ? "Скрыть" : "Показать"}
      </button>
    </div>
  </div>;
}
