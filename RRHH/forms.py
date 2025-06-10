from django import forms
from .models import Employee, TemporaryEmployee, ContractorEmployee, Department, Position



class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = '__all__'

class PositionForm(forms.ModelForm):
    class Meta:
        model = Position
        fields = '__all__'



class EmployeeForm(forms.ModelForm):
    class Meta:
        model = Employee
        fields = '__all__'

        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),

        }


class TemporaryEmployeeForm(forms.ModelForm):
    class Meta:
        model = TemporaryEmployee
        fields = '__all__'


class ContractorEmployeeForm(forms.ModelForm):
    class Meta:
        model = ContractorEmployee
        fields = '__all__'     