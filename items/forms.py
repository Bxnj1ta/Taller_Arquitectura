from django import forms
from decimal import Decimal
from datetime import datetime


class TopUpForm(forms.Form):
    full_name = forms.CharField(
        label="Nombre del titular",
        max_length=80,
        widget=forms.TextInput(attrs={"placeholder": "Nombre como aparece en la tarjeta"})
    )
    card_number = forms.CharField(
        label="Número de tarjeta",
        min_length=16,
        max_length=19,
        widget=forms.TextInput(attrs={"inputmode": "numeric", "placeholder": "4242 4242 4242 4242"})
    )
    expiry_month = forms.ChoiceField(
        label="Mes de expiración",
        choices=[(f"{i:02d}", f"{i:02d}") for i in range(1, 13)]
    )
    expiry_year = forms.ChoiceField(
        label="Año de expiración",
        choices=[(str(year), str(year)) for year in range(datetime.now().year, datetime.now().year + 11)]
    )
    cvv = forms.CharField(
        label="CVV",
        min_length=3,
        max_length=4,
        widget=forms.PasswordInput(attrs={"inputmode": "numeric", "placeholder": "123"})
    )
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('0.01'),
        label="Monto a agregar",
        widget=forms.NumberInput(attrs={"step": "0.01", "placeholder": "0.00"})
    )

    def clean_card_number(self):
        raw_number = self.cleaned_data["card_number"]
        digits = "".join(filter(str.isdigit, raw_number))
        if len(digits) != 16:
            raise forms.ValidationError("El número de tarjeta debe tener 16 dígitos.")
        return digits

    def clean_cvv(self):
        raw_cvv = self.cleaned_data["cvv"]
        digits = "".join(filter(str.isdigit, raw_cvv))
        if len(digits) not in (3, 4):
            raise forms.ValidationError("El CVV debe tener 3 o 4 dígitos.")
        return digits

    def clean(self):
        cleaned_data = super().clean()
        month = cleaned_data.get("expiry_month")
        year = cleaned_data.get("expiry_year")

        if month and year:
            now = datetime.now()
            exp_year = int(year)
            exp_month = int(month)

            if exp_year < now.year or (exp_year == now.year and exp_month < now.month):
                raise forms.ValidationError("La tarjeta está expirada.")

        return cleaned_data


class WithdrawForm(forms.Form):
    """Formulario para retirar dinero del wallet."""
    account_number = forms.CharField(
        label="Número de cuenta bancaria",
        max_length=20,
        min_length=8,
        widget=forms.TextInput(attrs={
            "placeholder": "Ej: 1234567890",
            "inputmode": "numeric"
        })
    )
    account_type = forms.ChoiceField(
        label="Tipo de cuenta",
        choices=[
            ("ahorros", "Cuenta de Ahorros"),
            ("corriente", "Cuenta Corriente"),
        ],
        widget=forms.Select(attrs={"class": "form-select"})
    )
    bank_name = forms.CharField(
        label="Banco",
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": "Ej: Bancolombia, Banco de Bogotá"})
    )
    amount = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=Decimal('0.01'),
        label="Monto a retirar",
        widget=forms.NumberInput(attrs={
            "step": "0.01",
            "placeholder": "0.00",
            "min": "0.01"
        })
    )

    def clean_account_number(self):
        account = self.cleaned_data["account_number"]
        # Solo permitir números
        if not account.isdigit():
            raise forms.ValidationError("El número de cuenta solo debe contener dígitos.")
        return account