import { useState } from "react";
import Button from "./Button";
const Card = (props) => {
  const [on, setOn] = useState(false);
  return (
    <>
      <h1 onClick={() => setOn((prev) => !prev)}>{on ? "🌞" : "🌜"}</h1>
      {console.log(on)}
      {/* on 이 true일때만 보이게  */}
      {/* !a 단항연산자 */}
      {/* a&&b,a||b 이항연산자 */}
      {/* a?b:c 삼항연산자 */}
      {on && <Button text="클릭" />}
      <div style={{ color: on && "red" }}>Card</div>
    </>
  );
};
export default Card;
