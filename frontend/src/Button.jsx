import "./Button.css";
const Button = ({ text, color }) => {
  // const cla = color === undefined ? "" : color;
  // text변수의 값이 "로그인" true "로그인❤" false text
  return (
    <>
      <div className={`btn ${color === undefined ? "" : color}`}>{`${text === "로그인" ? text + "❤" : text}`}</div>
      {text === "로그인" && <div>{text} 환영합니다</div>}
      {text === "회원가입" && <div>{text} 해주세요</div>}
    </>
  );
};
export default Button;
