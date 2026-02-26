
class PID:
    """
    Diskreter PID-Regler.
    Output = Kp*e + Ki*integral(e) + Kd*derivative(e)
    """
    def __init__(self, kp, ki, kd, min_out=None, max_out=None):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.min_out = min_out
        self.max_out = max_out
        
        self._integral = 0.0
        self._prev_error = 0.0

    def reset(self):
        self._integral = 0.0
        self._prev_error = 0.0

    def step(self, setpoint, measured, dt):
        if dt <= 0.0: return 0.0
        
        error = setpoint - measured
        
        # Proportional
        p_out = self.kp * error
        
        # Integral
        integral = self._integral
        self._integral += error * dt
        i_out = self.ki * self._integral

        # Derivative
        derivative = (error - self._prev_error) / dt
        d_out = self.kd * derivative
        
        output = p_out + i_out + d_out
        
        print(f"p_out: {p_out}, i_out: {i_out}, output: {output}")

        # Output Limiting (Clamping) & Anti-Windup (Conditional Integration)
        # Wenn der Output limitiert wird, korrigieren wir das Integral zurück ("Clamping")
        # damit es nicht sinnlos weiterläuft.
        
        limited = False
        if self.max_out is not None and output > self.max_out:
            output = self.max_out
            limited = True
        elif self.min_out is not None and output < self.min_out:
            output = self.min_out
            limited = True
            
        if limited:
            # Einfaches Anti-Windup: Integral macht den Schritt rückgängig
            # (bzw. wir akkumulieren nicht, wenn wir in Sättigung sind)
            # Hier: Simples "Zurückrechnen" oder einfach alten Wert behalten?
            # Wir machen conditional integration: Wenn Sättigung, integral nicht erhöhen.
            # Da wir oben schon erhöht haben, ziehen wir es wieder ab.
            # self._integral -= error * dt
            self._integral = integral
            
        self._prev_error = error
        return output
